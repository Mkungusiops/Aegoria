"""Test harness for domain-packs — reusable in a pack's own CI.

The goal: a pack author (or their CI) can answer one question with one call —
*does my sample data pass every quality gate my manifest declares?* — without
standing up cloud infra.

The harness works at two levels:

* :meth:`PackTestHarness.run_quality_gates` — the always-available path. It loads
  the manifest, reads each dataset's ``sample_data`` into an Arrow table, and
  evaluates the declared :class:`QualityRule` set with a small, self-contained
  evaluator. No adapters, no services, no warehouse — so it runs anywhere the SDK
  is installed and is what most pack CI should gate on.

* :meth:`PackTestHarness.bootstrap_engine` — the integration path. When the
  deployment's concrete providers are installed and discoverable, this builds a
  *temporary, isolated* :class:`AegoriaEngine` (warehouse + catalog under a temp
  dir), loads exactly this one pack, and hands it back so a pack can run a real
  end-to-end ingest+query. If the providers are not yet wired, it returns ``None``
  rather than failing the suite — the structural gates still run.

Both paths share the engine's own data vocabulary; the harness never re-implements
quality semantics that diverge from the core.
"""

from __future__ import annotations

import math
import re
import tempfile
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Optional

from aegoria_core.contracts.domain_pack import DatasetSpec, DomainPackManifest
from aegoria_core.contracts.models import (
    DatasetRef,
    QualityReport,
    QualityRule,
    RuleResult,
)

try:  # pyarrow ships with the engine's `lite` extra; sample data is read through it.
    import pyarrow as pa  # type: ignore
    import pyarrow.csv as pacsv  # type: ignore
    import pyarrow.compute as pc  # type: ignore
    import pyarrow.json as pajson  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - lite extra missing
    pa = None  # type: ignore
    pacsv = None  # type: ignore
    pc = None  # type: ignore
    pajson = None  # type: ignore


class TestkitError(Exception):
    """Raised for harness misuse (missing pyarrow, missing sample data path)."""


@dataclass
class HarnessResult:
    """Aggregate outcome of running quality gates across a pack's datasets."""

    pack_id: str
    reports: dict[str, QualityReport] = dc_field(default_factory=dict)
    skipped: dict[str, str] = dc_field(default_factory=dict)  # dataset -> reason
    errors: dict[str, str] = dc_field(default_factory=dict)   # dataset -> error message

    @property
    def passed(self) -> bool:
        """True iff every evaluated dataset passed all its *error*-severity rules.

        Datasets skipped for lack of sample data do not fail the run; missing data
        is an authoring gap surfaced by the linter, not a quality regression.
        """
        if self.errors:
            return False
        return all(report.passed for report in self.reports.values())

    @property
    def score(self) -> float:
        """Mean quality score across evaluated datasets (0..1)."""
        if not self.reports:
            return 0.0
        return sum(r.score for r in self.reports.values()) / len(self.reports)

    def render(self) -> str:
        lines = [f"Quality gates for {self.pack_id}: {'PASS' if self.passed else 'FAIL'}"]
        for name, report in self.reports.items():
            status = "ok" if report.passed else "FAIL"
            lines.append(f"  [{status:4}] {name}: score={report.score:.2f} ({len(report.results)} rule(s))")
            for r in report.results:
                if not r.passed:
                    lines.append(f"        - {r.rule_id}: {r.message} ({r.violations}/{r.sampled})")
        for name, reason in self.skipped.items():
            lines.append(f"  [skip] {name}: {reason}")
        for name, err in self.errors.items():
            lines.append(f"  [ERR ] {name}: {err}")
        return "\n".join(lines)


class PackTestHarness:
    """Spin up the minimal context needed to test exactly one domain-pack.

    Construct from a manifest path (the common case) or a loaded manifest::

        harness = PackTestHarness.from_path("domain-packs/climate-emissions")
        result = harness.run_quality_gates()
        assert result.passed, result.render()
    """

    def __init__(self, manifest: DomainPackManifest, *, base_dir: Path) -> None:
        self.manifest = manifest
        self.base_dir = Path(base_dir)  # sample_data paths resolve relative to this

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_path(cls, pack_path: str | Path) -> "PackTestHarness":
        """Build from a pack directory or a manifest.yaml path."""
        p = Path(pack_path)
        manifest_path = p / "manifest.yaml" if p.is_dir() else p
        manifest = DomainPackManifest.from_yaml(manifest_path)
        return cls(manifest, base_dir=manifest_path.parent)

    @classmethod
    def from_manifest(cls, manifest: DomainPackManifest, *, base_dir: str | Path = ".") -> "PackTestHarness":
        return cls(manifest, base_dir=Path(base_dir))

    # ------------------------------------------------------------------ #
    # Provider-free quality gates (always available)
    # ------------------------------------------------------------------ #
    def load_sample(self, dataset: DatasetSpec) -> Optional["pa.Table"]:
        """Read a dataset's declared ``sample_data`` into an Arrow table, or None.

        Format is inferred from the connector targeting the dataset (if any) or the
        file extension. Returns ``None`` when no sample_data is declared.
        """
        if pa is None:
            raise TestkitError("pyarrow is required to read sample data (install the engine 'lite' extra)")
        if not dataset.sample_data:
            return None
        path = (self.base_dir / dataset.sample_data).resolve()
        if not path.exists():
            raise TestkitError(f"sample_data for dataset {dataset.name!r} not found: {path}")
        fmt = self._sample_format(dataset, path)
        if fmt == "csv":
            return pacsv.read_csv(path)
        if fmt in ("json", "ndjson"):
            return pajson.read_json(path)
        if fmt == "parquet":
            import pyarrow.parquet as papq  # local import: only needed for parquet

            return papq.read_table(path)
        raise TestkitError(f"unsupported sample_data format {fmt!r} for dataset {dataset.name!r}")

    def _sample_format(self, dataset: DatasetSpec, path: Path) -> str:
        conn = next((c for c in self.manifest.connectors if c.target_dataset == dataset.name), None)
        if conn and conn.format:
            return conn.format.lower()
        return path.suffix.lstrip(".").lower() or "csv"

    def run_quality_gates(self, *, require_sample: bool = False) -> HarnessResult:
        """Evaluate every dataset's quality rules against its sample data.

        Args:
            require_sample: if True, a dataset without sample data is an error
                rather than a skip (use this in strict pack CI).
        """
        result = HarnessResult(pack_id=self.manifest.id)
        for ds in self.manifest.datasets:
            try:
                table = self.load_sample(ds)
            except TestkitError as exc:
                result.errors[ds.name] = str(exc)
                continue
            if table is None:
                msg = "no sample_data declared"
                if require_sample:
                    result.errors[ds.name] = msg
                else:
                    result.skipped[ds.name] = msg
                continue
            result.reports[ds.name] = self.evaluate(ds, table)
        return result

    def evaluate(self, dataset: DatasetSpec, table: "pa.Table") -> QualityReport:
        """Evaluate one dataset's :class:`QualityRule` list against an Arrow table.

        A self-contained evaluator covering the rule kinds the contract defines
        (``not_null | unique | range | regex | enum | freshness | referential``).
        Unknown / ``custom`` kinds are reported as passing with an informational
        message — they are the pack's own code hook's responsibility, not the
        declarative gate's.
        """
        ref = DatasetRef(domain=self.manifest.id, name=dataset.name, version=self.manifest.version)
        results = [self._eval_rule(rule, table) for rule in dataset.quality_rules]
        return QualityReport(dataset=ref, results=results)

    # -- per-rule evaluation -------------------------------------------- #
    def _eval_rule(self, rule: QualityRule, table: "pa.Table") -> RuleResult:
        n = table.num_rows
        col = table.column(rule.field) if rule.field and rule.field in table.column_names else None
        if rule.field and col is None and rule.kind in _FIELD_RULES:
            return RuleResult(
                rule_id=rule.id,
                passed=False,
                violations=n,
                sampled=n,
                message=f"field {rule.field!r} not present in sample data",
            )

        handler = _RULE_HANDLERS.get(rule.kind)
        if handler is None:
            return RuleResult(
                rule_id=rule.id,
                passed=True,
                sampled=n,
                message=f"rule kind {rule.kind!r} is not evaluated declaratively (custom hook)",
            )
        return handler(self, rule, table, col, n)

    def _r_not_null(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        violations = col.null_count
        return self._mk(rule, violations, n, "null values present")

    def _r_unique(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        distinct = pc.count_distinct(col).as_py()
        non_null = n - col.null_count
        violations = non_null - distinct
        return self._mk(rule, violations, n, "duplicate values present")

    def _r_range(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        lo = rule.params.get("min")
        hi = rule.params.get("max")
        mask = None
        if lo is not None:
            mask = pc.less(col, lo)
        if hi is not None:
            over = pc.greater(col, hi)
            mask = over if mask is None else pc.or_(mask, over)
        violations = 0 if mask is None else pc.sum(pc.cast(mask, pa.int64())).as_py() or 0
        return self._mk(rule, violations, n, f"values outside [{lo}, {hi}]")

    def _r_regex(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        pattern = rule.params.get("pattern")
        if not pattern:
            return RuleResult(rule_id=rule.id, passed=False, violations=n, sampled=n,
                              message="regex rule missing 'pattern' param")
        strcol = pc.cast(col, pa.string())
        matches = pc.match_substring_regex(strcol, pattern)
        # null cells neither match nor are counted as violations of a format rule
        non_null = pc.is_valid(strcol)
        bad = pc.and_(non_null, pc.invert(matches))
        violations = pc.sum(pc.cast(bad, pa.int64())).as_py() or 0
        return self._mk(rule, violations, n, f"values not matching /{pattern}/")

    def _r_enum(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        allowed = rule.params.get("values") or rule.params.get("allowed") or []
        if not allowed:
            return RuleResult(rule_id=rule.id, passed=False, violations=n, sampled=n,
                              message="enum rule missing 'values' param")
        member = pc.is_in(col, value_set=pa.array(allowed))
        non_null = pc.is_valid(col)
        bad = pc.and_(non_null, pc.invert(member))
        violations = pc.sum(pc.cast(bad, pa.int64())).as_py() or 0
        return self._mk(rule, violations, n, f"values outside allowed set {allowed}")

    def _r_freshness(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        # Declarative freshness can only sanity-check that the column parses as a
        # temporal type with no nulls; wall-clock thresholds belong to a live run.
        if not pa.types.is_temporal(col.type):
            try:
                pc.cast(col, pa.timestamp("us"))
            except Exception:
                return self._mk(rule, n, n, "freshness field is not timestamp-parseable")
        return self._mk(rule, col.null_count, n, "freshness field has null timestamps")

    def _r_referential(self, rule, table, col, n) -> RuleResult:  # noqa: ANN001
        # The referenced dataset is another sample; load + check membership if available.
        ref_ds_name = rule.params.get("ref_dataset")
        ref_field = rule.params.get("ref_field")
        ref_ds = self.manifest.dataset(ref_ds_name) if ref_ds_name else None
        if ref_ds is None or not ref_field:
            return RuleResult(rule_id=rule.id, passed=False, violations=n, sampled=n,
                              message=f"referential rule cannot resolve {ref_ds_name}.{ref_field}")
        try:
            ref_table = self.load_sample(ref_ds)
        except TestkitError as exc:
            return RuleResult(rule_id=rule.id, passed=True, sampled=n,
                              message=f"referential check skipped: {exc}")
        if ref_table is None or ref_field not in ref_table.column_names:
            return RuleResult(rule_id=rule.id, passed=True, sampled=n,
                              message="referential check skipped: referenced sample unavailable")
        valid_set = ref_table.column(ref_field).combine_chunks()
        member = pc.is_in(col, value_set=valid_set)
        non_null = pc.is_valid(col)
        bad = pc.and_(non_null, pc.invert(member))
        violations = pc.sum(pc.cast(bad, pa.int64())).as_py() or 0
        return self._mk(rule, violations, n, f"values not found in {ref_ds_name}.{ref_field}")

    def _mk(self, rule: QualityRule, violations: Any, sampled: int, fail_msg: str) -> RuleResult:
        v = int(violations or 0)
        passed = v == 0
        return RuleResult(
            rule_id=rule.id,
            passed=passed,
            violations=v,
            sampled=sampled,
            message="ok" if passed else fail_msg,
        )

    # ------------------------------------------------------------------ #
    # Integration path: a real, throwaway engine loading just this pack
    # ------------------------------------------------------------------ #
    def bootstrap_engine(self, *, tmp_dir: Optional[str | Path] = None) -> Optional[Any]:
        """Build an isolated :class:`AegoriaEngine` that has loaded *only* this pack.

        Returns a ready engine, or ``None`` when the deployment's concrete providers
        are not installed/discoverable (the structural + provider-free gates still
        run in that case, so a pack's CI is not blocked on infra availability).

        The engine's warehouse and catalog are redirected under ``tmp_dir`` (a fresh
        temp dir by default) so tests never touch a developer's real lakehouse.
        """
        try:
            from aegoria_core import AegoriaConfig, AegoriaEngine
            from aegoria_core.registry import load_entrypoints, registry
        except Exception:  # pragma: no cover - engine import shouldn't fail
            return None

        load_entrypoints()
        # If no providers are registered for the capabilities the engine needs,
        # bootstrapping will fail; detect that early and return None.
        described = registry.describe()
        required_adapters = {"catalog", "storage"}
        required_services = {"catalog"}
        have_adapters = set(described.get("adapters", {}))
        have_services = set(described.get("services", {}))
        if not required_adapters.issubset(have_adapters) or not required_services.issubset(have_services):
            return None

        root = Path(tmp_dir) if tmp_dir else Path(tempfile.mkdtemp(prefix="aegoria-pack-test-"))
        root.mkdir(parents=True, exist_ok=True)
        config = AegoriaConfig(
            deployment="lite",
            warehouse_uri=str(root / "warehouse"),
            catalog_uri=f"sqlite:///{root / 'catalog.db'}",
            domain_pack_paths=[],          # we load our single pack explicitly
            domain_packs=[self.manifest.id],
        )
        try:
            engine = AegoriaEngine.bootstrap(config, discover=False)
            engine.load_domain_pack(self.manifest)
        except Exception:  # provider wiring incomplete — fall back to provider-free gates
            return None
        return engine


# --------------------------------------------------------------------------- #
# Convenience: one-call CI gate
# --------------------------------------------------------------------------- #
def run_pack_quality_gates(pack_path: str | Path, *, require_sample: bool = False) -> HarnessResult:
    """Load the pack at ``pack_path`` and run its quality gates. One call for CI.

        result = run_pack_quality_gates("domain-packs/climate-emissions")
        assert result.passed, result.render()
    """
    return PackTestHarness.from_path(pack_path).run_quality_gates(require_sample=require_sample)


# Rule kinds that require a field column to be present.
_FIELD_RULES = {"not_null", "unique", "range", "regex", "enum", "freshness", "referential"}

# Dispatch table — keeps ``_eval_rule`` flat and the kinds easy to extend.
_RULE_HANDLERS = {
    "not_null": PackTestHarness._r_not_null,
    "unique": PackTestHarness._r_unique,
    "range": PackTestHarness._r_range,
    "regex": PackTestHarness._r_regex,
    "enum": PackTestHarness._r_enum,
    "freshness": PackTestHarness._r_freshness,
    "referential": PackTestHarness._r_referential,
}

# Silence unused-import linters for math/re kept available to handlers/extensions.
_ = (math, re)
