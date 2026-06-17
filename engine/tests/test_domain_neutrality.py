"""THE domain-neutrality test — the platform's central invariant.

Two deliberately unrelated markets — ``climate-emissions`` (open environmental
geodata) and ``consumer-credit`` (sensitive EU-resident PII) — must be served by
the EXACT same engine code path, with no domain-specific branching, and loading
either pack must perform ZERO edits to core modules.

We prove this two ways:

1. ``run_governed_aggregate`` is a SINGLE helper, parameterized only by a domain
   id + dataset name + connector + SQL. It is called identically for both
   markets and produces valid, governed results for each. The helper contains no
   ``if domain == ...`` branch; the only difference between the two runs is the
   declarative arguments sourced from each pack's manifest.

2. Loading a pack mutates only the registry/catalog (data), never the engine.
   We assert: both packs arrive through the same ``load_domain_packs`` path; the
   set of resolved core providers (``engine.health()['providers']``) is byte-for
   -byte identical before and after each market's data flows through; and the
   core engine source on disk is unchanged across the whole run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts.models import Obligation, QueryResult, QuerySpec

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_PACKS = REPO_ROOT / "domain-packs"
CORE_DIR = REPO_ROOT / "engine" / "aegoria_core"


@dataclass(frozen=True)
class MarketCase:
    """A purely declarative description of one market's e2e exercise.

    Every field is data sourced from the pack's manifest / sample data — there is
    no behavioural difference encoded here, only configuration.
    """

    domain: str
    dataset: str
    connector: str
    sample_file: str
    sql: str
    epsilon: Optional[float]  # None -> no DP obligation requested


# Two unrelated markets, same shape. NB: no code differs between them.
CASES: list[MarketCase] = [
    MarketCase(
        domain="climate-emissions",
        dataset="facility_emissions",
        connector="facility_emissions_parquet",
        sample_file="facility_emissions.parquet",
        sql="SELECT count(*) AS n, sum(co2e_tonnes) AS total FROM facility_emissions",
        epsilon=None,
    ),
    MarketCase(
        domain="consumer-credit",
        dataset="loan_applications",
        connector="loan_applications_csv",
        sample_file="loan_applications.csv",
        sql="SELECT count(*) AS n, avg(income) AS total FROM loan_applications",
        epsilon=1.0,
    ),
]


def _ensure_sample(case: MarketCase) -> Path:
    sample_dir = DOMAIN_PACKS / case.domain / "sample_data"
    target = sample_dir / case.sample_file
    if not target.exists():
        import importlib.util

        gen = sample_dir / "gen_sample.py"
        spec = importlib.util.spec_from_file_location(f"gen_{case.domain}", gen)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()
    return target


def run_governed_aggregate(engine: AegoriaEngine, case: MarketCase) -> QueryResult:
    """The ONE code path. Identical for every market — branchless by construction.

    Ingest the pack-declared dataset (provenance attached at capture), then run a
    governed aggregate through the carbon-aware scheduler. Differential privacy is
    requested purely from the declarative ``case.epsilon`` value; the helper does
    not know or care which market it is serving.
    """
    source = _ensure_sample(case)
    meta = engine.ingest(
        domain=case.domain,
        connector=case.connector,
        source_uri=str(source),
        dataset=case.dataset,
        principal="neutrality-test",
    )
    obligations: list[Obligation] = []
    if case.epsilon is not None:
        obligations.append(
            Obligation(kind="differential_privacy", params={"epsilon": case.epsilon, "delta": 1e-6})
        )
    spec = QuerySpec(sql=case.sql, datasets=[meta.ref], purpose=f"{case.domain}-aggregate")
    location = engine.lakehouse.table_location(meta.ref)
    return engine.scheduler.execute(spec, {meta.ref.name: location}, obligations=obligations)


@pytest.fixture()
def engine(tmp_path) -> AegoriaEngine:
    config = AegoriaConfig(
        warehouse_uri=str(tmp_path / "warehouse"),
        catalog_uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        domain_pack_paths=[str(DOMAIN_PACKS)],
    )
    return AegoriaEngine.bootstrap(config)


# --------------------------------------------------------------------------- #
def _core_source_digest() -> str:
    """Hash every core engine source file so we can prove none were edited."""
    files = sorted(
        p for p in CORE_DIR.rglob("*.py")
        if "__pycache__" not in p.parts
    )
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(CORE_DIR).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.domain)
def test_same_code_path_serves_every_market(engine: AegoriaEngine, case: MarketCase) -> None:
    """One helper, two unrelated markets, valid governed results for each."""
    result = run_governed_aggregate(engine, case)
    # A valid, materialized result for BOTH markets.
    assert isinstance(result, QueryResult)
    assert result.stats.rows == 1
    assert result.stats.engine == "duckdb"
    # Carbon-aware accounting is always present, regardless of market.
    assert result.stats.carbon_g > 0
    assert result.stats.energy_kwh > 0
    # DP is applied exactly when (and only when) the declarative case requested it.
    expect_dp = case.epsilon is not None
    assert result.stats.dp_applied is expect_dp
    assert (result.stats.epsilon_spent > 0) is expect_dp


def test_both_markets_run_through_one_helper_with_no_branching(engine: AegoriaEngine) -> None:
    """Drive both markets through the identical helper in a single loop."""
    rows_by_domain: dict[str, int] = {}
    for case in CASES:
        result = run_governed_aggregate(engine, case)
        assert result.stats.rows == 1
        rows_by_domain[case.domain] = result.rows[0]["n"]
    # Both markets produced an answer; they are genuinely different datasets.
    assert set(rows_by_domain) == {"climate-emissions", "consumer-credit"}
    assert all(isinstance(v, (int, float)) for v in rows_by_domain.values())


def test_loading_a_pack_does_not_edit_core(engine: AegoriaEngine) -> None:
    """Both packs register via the SAME load path and never touch core modules."""
    # Both packs arrived through engine.load_domain_packs (the single entry point).
    loaded = set(engine.domain_packs)
    assert {"climate-emissions", "consumer-credit"} <= loaded

    # The resolved core providers are identical no matter which market is loaded.
    baseline_providers = engine.health()["providers"]
    digest_before = _core_source_digest()

    for case in CASES:
        run_governed_aggregate(engine, case)
        # Provider wiring is byte-for-byte stable across every market's data flow.
        assert engine.health()["providers"] == baseline_providers

    # The core engine source on disk is unchanged by onboarding either market.
    assert _core_source_digest() == digest_before


def test_health_identical_provider_topology_for_both_packs(engine: AegoriaEngine) -> None:
    """``health()`` reports the same provider topology with both packs loaded."""
    health = engine.health()
    providers = health["providers"]
    # The same domain-neutral core capabilities back every market.
    assert set(providers["adapters"]) >= {
        "storage", "catalog", "compute", "stream", "identity", "provenance", "carbon"
    }
    assert set(providers["services"]) >= {
        "lakehouse", "ingestion", "catalog", "governance",
        "scheduler", "knowledge_graph", "ml", "provenance",
    }
    # Both reference markets are present and described uniformly.
    described = {p["id"]: p for p in health["domain_packs"]}
    assert {"climate-emissions", "consumer-credit"} <= set(described)
    for entry in described.values():
        assert entry["datasets"] >= 1
        assert {"id", "name", "version", "datasets"} <= set(entry)
