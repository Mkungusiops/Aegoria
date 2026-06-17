"""End-to-end test over BOTH reference domains via the engine's PUBLIC API.

Mirrors ``examples/e2e_demo.py`` with hard assertions:

* both packs load and ingest > 0 rows (climate + consumer-credit),
* provenance (checksum + signature) is attached at capture,
* a climate aggregate runs through the carbon-aware scheduler and is placed on
  the greenest region with non-zero carbon accounting,
* a consumer-credit aggregate runs UNDER differential privacy with epsilon spent
  and PII masking applied (real engine machinery, no test-local privacy logic),
* a raw row-level PII SELECT on consumer-credit is DENIED by governance,
* ingest records a lineage edge,
* a C2PA-style signature verifies and tampering is rejected.

Everything talks to ``AegoriaEngine`` through its public surface only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts.models import (
    AccessRequest,
    Action,
    Obligation,
    Principal,
    ProvenanceRecord,
    QuerySpec,
)
from aegoria_core.errors import AccessDenied

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_PACKS = REPO_ROOT / "domain-packs"


def _ensure_sample(domain: str, filename: str) -> Path:
    """Return a pack sample file, generating the pack's data if absent."""
    sample_dir = DOMAIN_PACKS / domain / "sample_data"
    target = sample_dir / filename
    if not target.exists():
        import importlib.util

        gen = sample_dir / "gen_sample.py"
        spec = importlib.util.spec_from_file_location(f"gen_{domain}", gen)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()
    return target


@pytest.fixture()
def engine(tmp_path) -> AegoriaEngine:
    config = AegoriaConfig(
        warehouse_uri=str(tmp_path / "warehouse"),
        catalog_uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        domain_pack_paths=[str(DOMAIN_PACKS)],
    )
    return AegoriaEngine.bootstrap(config)


@pytest.fixture()
def both_domains(engine: AegoriaEngine):
    """Ingest one dataset per market and return their metadata."""
    _ensure_sample("climate-emissions", "facility_emissions.parquet")
    _ensure_sample("consumer-credit", "loan_applications.csv")
    climate = engine.ingest(
        domain="climate-emissions",
        connector="facility_emissions_parquet",
        source_uri=str(DOMAIN_PACKS / "climate-emissions" / "sample_data" / "facility_emissions.parquet"),
        dataset="facility_emissions",
        principal="gen_sample.py",
    )
    credit = engine.ingest(
        domain="consumer-credit",
        connector="loan_applications_csv",
        source_uri=str(DOMAIN_PACKS / "consumer-credit" / "sample_data" / "loan_applications.csv"),
        dataset="loan_applications",
        principal="gen_sample.py",
    )
    return climate, credit


# --------------------------------------------------------------------------- #
def test_both_packs_load(engine: AegoriaEngine) -> None:
    packs = {p["id"] for p in engine.health()["domain_packs"]}
    assert {"climate-emissions", "consumer-credit"} <= packs


def test_ingest_both_domains_rows_and_provenance(both_domains) -> None:
    climate, credit = both_domains
    # rows > 0 for BOTH unrelated markets.
    assert climate.row_count > 0
    assert credit.row_count > 0
    # Provenance attached AT CAPTURE: checksum + cryptographic signature.
    for meta in (climate, credit):
        rec = meta.provenance[-1]
        assert rec.checksum_sha256, f"{meta.ref.id} missing capture checksum"
        assert rec.content_signature, f"{meta.ref.id} missing capture signature"
        assert rec.signature_alg


def test_climate_query_is_carbon_aware(engine: AegoriaEngine, both_domains) -> None:
    climate, _ = both_domains
    spec = QuerySpec(
        sql="SELECT count(*) AS readings, sum(co2e_tonnes) AS total FROM facility_emissions",
        datasets=[climate.ref],
        purpose="emissions-report",
    )
    result = engine.query(spec)
    assert result.stats.rows == 1
    assert result.stats.engine == "duckdb"
    # Carbon accounting is real and non-zero.
    assert result.stats.carbon_g > 0
    assert result.stats.energy_kwh > 0
    # The greenest available region is chosen.
    greenest = min(engine.carbon_snapshot(), key=lambda r: r.gco2_per_kwh)
    assert result.stats.region == greenest.region


def test_consumer_credit_aggregate_under_differential_privacy(engine: AegoriaEngine, both_domains) -> None:
    _, credit = both_domains
    location = engine.lakehouse.table_location(credit.ref)
    spec = QuerySpec(
        sql="SELECT decision, count(*) AS n, avg(income) AS avg_income FROM loan_applications GROUP BY decision",
        datasets=[credit.ref],
        purpose="portfolio-analyst",
    )
    obligations = [
        Obligation(kind="differential_privacy", params={"epsilon": 1.0, "delta": 1e-6}),
        Obligation(kind="mask", params={"fields": credit.schema_.pii_fields, "strategy": "hash"}),
    ]
    result = engine.scheduler.execute(spec, {"loan_applications": location}, obligations=obligations)
    # DP applied + epsilon spent + budget recorded.
    assert result.stats.dp_applied is True
    assert result.stats.epsilon_spent == pytest.approx(1.0)
    budget = engine.governance.budget("portfolio-analyst", credit.ref)
    assert budget.spent == pytest.approx(1.0)
    # Aggregate still close to truth despite calibrated noise.
    total = sum(row["n"] for row in result.rows)
    assert total == pytest.approx(credit.row_count, abs=200)

    # PII columns are blocked: masking redacts identifiers entirely.
    raw = engine.lakehouse.scan(credit.ref, columns=["email"]).slice(0, 5)
    masked = engine.governance.apply_obligations(
        raw,
        [Obligation(kind="mask", params={"fields": ["email"], "strategy": "hash"})],
        schema=credit.schema_,
    )
    masked_emails = masked.column("email").to_pylist()
    assert all("@" not in v for v in masked_emails)
    assert set(raw.column("email").to_pylist()).isdisjoint(masked_emails)


def test_raw_pii_select_is_denied(engine: AegoriaEngine, both_domains) -> None:
    _, credit = both_domains
    analyst = Principal(
        subject="analyst-1",
        roles=["analyst"],
        jurisdiction="EU",
        attributes={"region": "EU", "purpose": "analytics"},
    )
    spec = QuerySpec(
        sql="SELECT application_id, applicant_name, national_id, email FROM loan_applications LIMIT 10",
        datasets=[credit.ref],
        purpose="raw-pii-pull",
    )
    with pytest.raises(AccessDenied):
        engine.query(spec, analyst)

    # Governance denies the raw read directly as well.
    meta = engine.catalog.get(credit.ref)
    decision = engine.governance.authorize(
        AccessRequest(principal=analyst, dataset=credit.ref, action=Action.READ, purpose="raw-pii-pull"),
        meta,
    )
    assert decision.allow is False
    assert decision.reason


def test_lineage_edges_exist(engine: AegoriaEngine, both_domains) -> None:
    climate, credit = both_domains
    for meta in (climate, credit):
        edges = engine.catalog.lineage(meta.ref)
        assert edges, f"no lineage recorded for {meta.ref.id}"
        assert any(e.operation == "ingest" and e.dst.name == meta.ref.name for e in edges)


def test_signature_verifies_and_tamper_rejected(engine: AegoriaEngine, both_domains) -> None:
    climate, _ = both_domains
    chain = engine.provenance.chain(climate.ref)
    assert chain, "provenance chain must contain the capture record"
    payload = b"aegoria-c2pa-demo-asset"
    signed = engine.provenance.sign_asset(payload, ProvenanceRecord(source_uri=str(climate.ref)))
    assert engine.provenance.verify_asset(payload, signed)["valid"] is True
    # Any tampering with the bytes invalidates the signature.
    assert engine.provenance.verify_asset(payload + b"x", signed)["valid"] is False
