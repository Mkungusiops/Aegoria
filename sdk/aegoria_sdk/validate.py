"""Structural validation + linting for domain-pack manifests.

The engine trusts a manifest the moment it loads it, so the cost of a malformed
pack is paid at runtime in production. This module moves that cost left: it loads
a manifest through the *same* ``DomainPackManifest.from_yaml`` the engine uses and
then asserts the cross-references hold together before anyone ships it.

Two layers:

* ``validate_manifest`` — hard structural checks. A pack that fails these would
  break or silently misbehave inside the engine (dangling dataset references,
  quality rules over fields that do not exist, an unparseable ``core_compat``).
  These produce ``ERROR`` issues.

* ``lint_manifest`` — everything in ``validate_manifest`` plus best-practice
  advisories (``WARNING`` / ``INFO``): missing FAIR metadata, undocumented PII,
  unmapped fields, datasets without quality gates. Advisories never block.

Both return a :class:`ValidationReport`; ``report.ok`` is true when there are no
``ERROR`` issues. Nothing here imports the engine — validation is pure manifest
analysis against the frozen ``aegoria_core`` contracts.
"""

from __future__ import annotations

import fnmatch
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from aegoria_core.contracts.domain_pack import DomainPackManifest
from aegoria_core.contracts.models import Sensitivity

try:  # `packaging` ships with aegoria-core; used to mirror the engine's compat check.
    from packaging.specifiers import SpecifierSet
except ModuleNotFoundError:  # pragma: no cover - defensive
    SpecifierSet = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Report model
# --------------------------------------------------------------------------- #
class Severity(str, Enum):
    """How much an issue matters. Only ``ERROR`` blocks ``report.ok``."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Stable machine-readable codes so CI / the console can filter & dedupe issues.
class Code:
    LOAD_FAILED = "E001-load-failed"
    DUP_DATASET = "E002-duplicate-dataset"
    DUP_FIELD = "E003-duplicate-field"
    MAPPING_DATASET_MISSING = "E004-mapping-dataset-missing"
    MAPPING_FIELD_MISSING = "E005-mapping-field-missing"
    MAPPING_TERM_MISSING = "E006-mapping-term-missing"
    CONNECTOR_TARGET_MISSING = "E007-connector-target-missing"
    QUALITY_FIELD_MISSING = "E008-quality-field-missing"
    CORE_COMPAT_INVALID = "E009-core-compat-invalid"
    MODEL_TARGET_MISSING = "E010-model-target-missing"
    PK_FIELD_MISSING = "E011-primary-key-field-missing"
    PARTITION_FIELD_MISSING = "E012-partition-field-missing"
    DUP_ID = "E013-duplicate-id"
    ONTOLOGY_PARENT_MISSING = "E014-ontology-parent-missing"

    # Linter advisories.
    NO_DATASETS = "W101-no-datasets"
    NO_QUALITY_RULES = "W102-no-quality-rules"
    PII_NOT_CLASSIFIED = "W103-pii-not-classified"
    NO_DESCRIPTION = "W104-missing-description"
    NO_ACCESS_POLICY = "W105-no-access-policy"
    POLICY_DATASET_NO_MATCH = "W106-policy-dataset-no-match"
    UNMAPPED_FIELD = "I201-field-unmapped"
    MODALITY_NOT_DECLARED = "I202-modality-not-declared"
    NO_SAMPLE_DATA = "I203-no-sample-data"


class ValidationIssue(BaseModel):
    """A single finding, with enough context to fix it without re-reading the file."""

    severity: Severity
    code: str
    message: str
    location: str = ""  # dotted path into the manifest, e.g. "datasets[2].quality_rules[0]"

    def __str__(self) -> str:  # noqa: D401 - rendered by the CLI / CI logs
        where = f" ({self.location})" if self.location else ""
        return f"[{self.severity.value.upper():7}] {self.code}: {self.message}{where}"


class ValidationReport(BaseModel):
    """The outcome of validating one manifest."""

    pack_id: Optional[str] = None
    manifest_path: Optional[str] = None
    issues: list[ValidationIssue] = Field(default_factory=list)

    # -- convenience accessors --------------------------------------------- #
    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.INFO]

    @property
    def ok(self) -> bool:
        """True iff there are no blocking (``ERROR``) issues."""
        return not self.errors

    def summary(self) -> str:
        return (
            f"{len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), "
            f"{len(self.infos)} info"
        )

    def render(self) -> str:
        """A multi-line human report suitable for stdout / CI logs."""
        head = f"Domain-pack {self.pack_id or '<unknown>'}: {self.summary()}"
        if not self.issues:
            return head + "\n  no issues found."
        body = "\n".join(f"  {issue}" for issue in self.issues)
        return f"{head}\n{body}"


# --------------------------------------------------------------------------- #
# Internal builder so error/warning/info helpers stay terse.
# --------------------------------------------------------------------------- #
class _Issues:
    def __init__(self) -> None:
        self.items: list[ValidationIssue] = []

    def error(self, code: str, message: str, location: str = "") -> None:
        self.items.append(ValidationIssue(severity=Severity.ERROR, code=code, message=message, location=location))

    def warn(self, code: str, message: str, location: str = "") -> None:
        self.items.append(ValidationIssue(severity=Severity.WARNING, code=code, message=message, location=location))

    def info(self, code: str, message: str, location: str = "") -> None:
        self.items.append(ValidationIssue(severity=Severity.INFO, code=code, message=message, location=location))


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def validate_path(path: str | Path, *, lint: bool = False) -> ValidationReport:
    """Load a manifest from ``path`` and validate (optionally lint) it.

    Loading goes through ``DomainPackManifest.from_yaml`` — the exact code path the
    engine uses — so a pack that loads here loads in production. A load/parse
    failure is reported as a single blocking issue rather than raising.
    """
    path = Path(path)
    try:
        manifest = DomainPackManifest.from_yaml(path)
    except FileNotFoundError:
        report = ValidationReport(manifest_path=str(path))
        report.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code=Code.LOAD_FAILED,
                message=f"manifest file not found: {path}",
            )
        )
        return report
    except ValidationError as exc:
        report = ValidationReport(manifest_path=str(path))
        report.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code=Code.LOAD_FAILED,
                message=f"manifest failed schema validation: {exc.error_count()} error(s) — {_first_pydantic_error(exc)}",
            )
        )
        return report
    except Exception as exc:  # malformed YAML, wrong top-level type, etc.
        report = ValidationReport(manifest_path=str(path))
        report.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code=Code.LOAD_FAILED,
                message=f"could not load manifest: {exc}",
            )
        )
        return report

    report = lint_manifest(manifest) if lint else validate_manifest(manifest)
    report.manifest_path = str(path)
    return report


def validate_manifest(manifest: DomainPackManifest) -> ValidationReport:
    """Run the hard structural checks against an already-loaded manifest.

    These are the invariants the engine assumes when it loads a pack:

    * dataset names are unique, and so are field names within a dataset;
    * ids (ontology terms, connectors, models, policies) are unique;
    * every ``semantic_mapping`` points at a real dataset + field (+ ontology term);
    * every ``connector.target_dataset`` and ``model.target_dataset`` resolves;
    * every quality rule's ``field`` (when set) exists in its dataset schema;
    * each schema's ``primary_key`` / ``partition_by`` reference real fields;
    * ``core_compat`` is a parseable semver specifier.
    """
    iss = _Issues()
    _check_ids_unique(manifest, iss)
    by_name = _check_datasets(manifest, iss)
    _check_semantic_mappings(manifest, by_name, iss)
    _check_connectors(manifest, by_name, iss)
    _check_models(manifest, by_name, iss)
    _check_core_compat(manifest, iss)
    _check_ontology(manifest, iss)
    return ValidationReport(pack_id=manifest.id, issues=iss.items)


def lint_manifest(manifest: DomainPackManifest) -> ValidationReport:
    """Structural validation plus best-practice advisories (warnings + info)."""
    report = validate_manifest(manifest)
    iss = _Issues()
    iss.items = report.issues  # keep structural issues, append advisories
    _lint_advisories(manifest, iss)
    return ValidationReport(pack_id=manifest.id, issues=iss.items, manifest_path=report.manifest_path)


# --------------------------------------------------------------------------- #
# Structural checks
# --------------------------------------------------------------------------- #
def _check_ids_unique(manifest: DomainPackManifest, iss: _Issues) -> None:
    """Each id-bearing collection must have unique ids (the engine keys by id)."""
    for label, items in (
        ("ontology", manifest.ontology),
        ("connectors", manifest.connectors),
        ("models", manifest.models),
        ("access_policies", manifest.access_policies),
    ):
        seen: set[str] = set()
        for idx, item in enumerate(items):
            ident = item.id
            if ident in seen:
                iss.error(Code.DUP_ID, f"duplicate id {ident!r} in {label}", f"{label}[{idx}]")
            seen.add(ident)


def _check_datasets(manifest: DomainPackManifest, iss: _Issues) -> dict[str, object]:
    """Validate dataset uniqueness + schema internal consistency. Returns name->dataset."""
    by_name: dict[str, object] = {}
    for idx, ds in enumerate(manifest.datasets):
        loc = f"datasets[{idx}]"
        if ds.name in by_name:
            iss.error(Code.DUP_DATASET, f"duplicate dataset name {ds.name!r}", loc)
        by_name[ds.name] = ds

        field_names: set[str] = set()
        for f_idx, field in enumerate(ds.schema_.fields):
            if field.name in field_names:
                iss.error(
                    Code.DUP_FIELD,
                    f"duplicate field {field.name!r} in dataset {ds.name!r}",
                    f"{loc}.schema.fields[{f_idx}]",
                )
            field_names.add(field.name)

        for pk in ds.schema_.primary_key:
            if pk not in field_names:
                iss.error(
                    Code.PK_FIELD_MISSING,
                    f"primary_key field {pk!r} is not a field of dataset {ds.name!r}",
                    f"{loc}.schema.primary_key",
                )
        for part in ds.schema_.partition_by:
            if part not in field_names:
                iss.error(
                    Code.PARTITION_FIELD_MISSING,
                    f"partition_by field {part!r} is not a field of dataset {ds.name!r}",
                    f"{loc}.schema.partition_by",
                )

        _check_quality_rules(ds, field_names, loc, iss)
    return by_name


def _check_quality_rules(ds: object, field_names: set[str], loc: str, iss: _Issues) -> None:
    """A quality rule that names a non-existent field would crash the quality gate."""
    rules = getattr(ds, "quality_rules", [])
    for r_idx, rule in enumerate(rules):
        if rule.field is not None and rule.field not in field_names:
            iss.error(
                Code.QUALITY_FIELD_MISSING,
                f"quality rule {rule.id!r} targets field {rule.field!r} "
                f"which is not in dataset {getattr(ds, 'name', '?')!r}",
                f"{loc}.quality_rules[{r_idx}]",
            )
        # Referential rules reference another dataset/field via params; surface a
        # required-key check so the rule can actually run.
        if rule.kind == "referential":
            missing = [k for k in ("ref_dataset", "ref_field") if k not in rule.params]
            if missing:
                iss.error(
                    Code.QUALITY_FIELD_MISSING,
                    f"referential rule {rule.id!r} missing params {missing}",
                    f"{loc}.quality_rules[{r_idx}]",
                )


def _check_semantic_mappings(manifest: DomainPackManifest, by_name: dict[str, object], iss: _Issues) -> None:
    term_ids = {t.id for t in manifest.ontology}
    for idx, mapping in enumerate(manifest.semantic_mappings):
        loc = f"semantic_mappings[{idx}]"
        ds = by_name.get(mapping.dataset)
        if ds is None:
            iss.error(
                Code.MAPPING_DATASET_MISSING,
                f"semantic mapping references unknown dataset {mapping.dataset!r}",
                loc,
            )
            continue
        if ds.schema_.field(mapping.field) is None:  # type: ignore[attr-defined]
            iss.error(
                Code.MAPPING_FIELD_MISSING,
                f"semantic mapping references field {mapping.field!r} "
                f"absent from dataset {mapping.dataset!r}",
                loc,
            )
        if term_ids and mapping.term not in term_ids:
            iss.error(
                Code.MAPPING_TERM_MISSING,
                f"semantic mapping references ontology term {mapping.term!r} "
                f"not declared in this pack",
                loc,
            )


def _check_connectors(manifest: DomainPackManifest, by_name: dict[str, object], iss: _Issues) -> None:
    for idx, conn in enumerate(manifest.connectors):
        if conn.target_dataset and conn.target_dataset not in by_name:
            iss.error(
                Code.CONNECTOR_TARGET_MISSING,
                f"connector {conn.id!r} targets unknown dataset {conn.target_dataset!r}",
                f"connectors[{idx}]",
            )


def _check_models(manifest: DomainPackManifest, by_name: dict[str, object], iss: _Issues) -> None:
    for idx, model in enumerate(manifest.models):
        if model.target_dataset and model.target_dataset not in by_name:
            iss.error(
                Code.MODEL_TARGET_MISSING,
                f"model {model.id!r} targets unknown dataset {model.target_dataset!r}",
                f"models[{idx}]",
            )


def _check_core_compat(manifest: DomainPackManifest, iss: _Issues) -> None:
    """Mirror ``AegoriaEngine._check_compat``: an unparseable specifier is fatal."""
    if SpecifierSet is None:  # pragma: no cover - packaging always present via core
        return
    try:
        SpecifierSet(manifest.core_compat)
    except Exception as exc:
        iss.error(
            Code.CORE_COMPAT_INVALID,
            f"core_compat {manifest.core_compat!r} is not a valid version specifier: {exc}",
            "core_compat",
        )


def _check_ontology(manifest: DomainPackManifest, iss: _Issues) -> None:
    """A term's ``parent`` must resolve to another term in the same pack (if set)."""
    term_ids = {t.id for t in manifest.ontology}
    for idx, term in enumerate(manifest.ontology):
        if term.parent and term.parent not in term_ids:
            iss.error(
                Code.ONTOLOGY_PARENT_MISSING,
                f"ontology term {term.id!r} has parent {term.parent!r} not declared in this pack",
                f"ontology[{idx}]",
            )


# --------------------------------------------------------------------------- #
# Linter advisories (non-blocking)
# --------------------------------------------------------------------------- #
def _lint_advisories(manifest: DomainPackManifest, iss: _Issues) -> None:
    if not manifest.description:
        iss.warn(Code.NO_DESCRIPTION, "pack has no top-level description", "description")
    if not manifest.datasets:
        iss.warn(Code.NO_DATASETS, "pack declares no datasets — there is nothing to onboard")
    if not manifest.access_policies:
        iss.warn(
            Code.NO_ACCESS_POLICY,
            "pack ships no access policies; the platform will fall back to engine defaults",
        )

    mapped = {(m.dataset, m.field) for m in manifest.semantic_mappings}
    declared_modalities = set(manifest.modalities)

    for idx, ds in enumerate(manifest.datasets):
        loc = f"datasets[{idx}]"
        if not ds.description:
            iss.warn(Code.NO_DESCRIPTION, f"dataset {ds.name!r} has no description", loc)
        if not ds.quality_rules:
            iss.warn(
                Code.NO_QUALITY_RULES,
                f"dataset {ds.name!r} has no quality rules; its quality gate is a no-op",
                loc,
            )
        if not ds.sample_data:
            iss.info(
                Code.NO_SAMPLE_DATA,
                f"dataset {ds.name!r} ships no sample_data; pack CI cannot exercise its quality gate",
                loc,
            )
        if ds.modality not in declared_modalities:
            iss.info(
                Code.MODALITY_NOT_DECLARED,
                f"dataset {ds.name!r} uses modality {ds.modality.value!r} "
                f"not listed in the pack's top-level modalities",
                loc,
            )
        for f_idx, field in enumerate(ds.schema_.fields):
            floc = f"{loc}.schema.fields[{f_idx}]"
            is_pii = field.pii or field.sensitivity in (Sensitivity.PII, Sensitivity.PHI)
            if is_pii and not field.pii:
                iss.warn(
                    Code.PII_NOT_CLASSIFIED,
                    f"field {ds.name}.{field.name} is {field.sensitivity.value} "
                    f"but pii flag is not set; set pii: true so obligations apply",
                    floc,
                )
            if manifest.ontology and (ds.name, field.name) not in mapped:
                iss.info(
                    Code.UNMAPPED_FIELD,
                    f"field {ds.name}.{field.name} has no semantic mapping; "
                    f"it will not participate in cross-domain interoperability",
                    floc,
                )

    dataset_names = [d.name for d in manifest.datasets]
    for idx, policy in enumerate(manifest.access_policies):
        if policy.datasets and not _any_glob_match(policy.datasets, dataset_names):
            iss.warn(
                Code.POLICY_DATASET_NO_MATCH,
                f"access policy {policy.id!r} dataset patterns {policy.datasets} "
                f"match none of the pack's datasets",
                f"access_policies[{idx}]",
            )


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _any_glob_match(patterns: list[str], names: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns for name in names)


def _first_pydantic_error(exc: ValidationError) -> str:
    errs = exc.errors()
    if not errs:
        return str(exc)
    first = errs[0]
    loc = ".".join(str(p) for p in first.get("loc", ()))
    return f"{loc}: {first.get('msg', '')}".strip(": ")
