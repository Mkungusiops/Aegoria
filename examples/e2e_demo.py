#!/usr/bin/env python
"""Aegoria end-to-end demo — one engine, two unrelated markets, zero core edits.

This script proves the platform's central claim: the **same** domain-neutral core
engine ingests, governs, schedules and queries two completely unrelated markets —
``climate-emissions`` (open environmental data) and ``consumer-credit`` (highly
sensitive, EU-resident PII) — purely by loading their declarative domain-packs.
Nothing below branches on the market; the difference in behaviour comes entirely
from each pack's manifest (schemas, sensitivities, jurisdictions and policies).

It talks to the engine through its PUBLIC API only:

    AegoriaEngine.bootstrap() / .ingest() / .query() / .catalog / .health()
    .lakehouse / .governance / .scheduler / .provenance   (resolved services)

Run it against a throwaway warehouse::

    /Users/jeff/Code/Aegoria/engine/.venv/bin/python \
        /Users/jeff/Code/Aegoria/examples/e2e_demo.py

The output is organised into numbered sections matching the demo narrative.

A note on consumer-credit governance
-------------------------------------
The consumer-credit pack ships a ``deny_processing_outside_eu`` policy that denies
only when ``principal.jurisdiction != 'EU'`` — ``DefaultGovernance`` evaluates the
policy ``condition`` expression, so an EU-resident analyst is ALLOWED (section 4a)
with the manifest's ``differential_privacy`` + ``mask`` obligations enforced by
``scheduler.execute``, while a raw row-level PII projection is DENIED (section 4b)
by the privacy gate (a non-owner may not pull raw PII columns; aggregate or use a
de-identified query). No demo-specific privacy logic is implemented here — only
real engine code runs.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import structlog

# Silence structured logging so the narrative stays readable.
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))

from aegoria_core import AegoriaConfig, AegoriaEngine  # noqa: E402
from aegoria_core.contracts.models import (  # noqa: E402
    AccessRequest,
    Action,
    Obligation,
    Principal,
    ProvenanceRecord,
    QuerySpec,
)
from aegoria_core.errors import AccessDenied  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_PACKS = REPO_ROOT / "domain-packs"


def _rule(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def _kv(label: str, value: Any) -> None:
    print(f"  {label:<28} {value}")


# --------------------------------------------------------------------------- #
# Sample-data generation (delegates to each pack's own gen_sample.py).
# --------------------------------------------------------------------------- #
def ensure_sample_data() -> None:
    """Generate each pack's deterministic sample files if they are missing.

    The generators are the packs' own ``sample_data/gen_sample.py`` modules — the
    demo never fabricates domain data itself.
    """
    import importlib.util

    targets = [
        (DOMAIN_PACKS / "climate-emissions" / "sample_data", "facility_emissions.parquet"),
        (DOMAIN_PACKS / "consumer-credit" / "sample_data", "loan_applications.csv"),
    ]
    for sample_dir, sentinel in targets:
        if (sample_dir / sentinel).exists():
            continue
        gen = sample_dir / "gen_sample.py"
        spec = importlib.util.spec_from_file_location(f"gen_{sample_dir.parent.name}", gen)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()


# --------------------------------------------------------------------------- #
# A single, domain-NEUTRAL ingest helper. No `if domain == ...` anywhere.
# --------------------------------------------------------------------------- #
def ingest_sample(
    engine: AegoriaEngine, *, domain: str, connector: str, dataset: str, filename: str
) -> Any:
    """Ingest one pack-declared dataset from its bundled sample file.

    Identical code path for both markets: resolve the source file, call
    ``engine.ingest`` (which attaches provenance + a lineage edge at capture).
    """
    source = DOMAIN_PACKS / domain / "sample_data" / filename
    return engine.ingest(
        domain=domain,
        connector=connector,
        source_uri=str(source),
        dataset=dataset,
        principal="gen_sample.py",
    )


def main() -> None:
    _rule("AEGORIA END-TO-END DEMO — domain-neutral lakehouse, two unrelated markets")

    ensure_sample_data()
    workdir = Path(tempfile.mkdtemp(prefix="aegoria-e2e-"))
    config = AegoriaConfig(
        warehouse_uri=str(workdir / "warehouse"),
        catalog_uri=f"sqlite:///{workdir / 'catalog.db'}",
        domain_pack_paths=[str(DOMAIN_PACKS)],
    )

    # ---------------------------------------------------------------- #
    # 1) Bootstrap: discover providers, wire services, load both packs.
    # ---------------------------------------------------------------- #
    _rule("1) BOOTSTRAP — resolve providers from the registry, load domain-packs")
    engine = AegoriaEngine.bootstrap(config)
    health = engine.health()
    providers = health["providers"]
    _kv("core version", health["core_version"])
    _kv("deployment", health["deployment"])
    _kv("adapters", ", ".join(sorted(providers["adapters"])))
    _kv("services", ", ".join(sorted(providers["services"])))
    loaded_packs = [p["id"] for p in health["domain_packs"]]
    _kv("domain-packs loaded", ", ".join(loaded_packs))
    assert "climate-emissions" in loaded_packs and "consumer-credit" in loaded_packs
    print("  -> Same engine, two markets onboarded purely from manifests.")

    # ---------------------------------------------------------------- #
    # 2) Ingest sample data for BOTH domains via the SAME code path.
    # ---------------------------------------------------------------- #
    _rule("2) INGEST — multi-modal capture with provenance attached at source")
    plan = [
        ("climate-emissions", "facility_emissions_parquet", "facility_emissions", "facility_emissions.parquet"),
        ("climate-emissions", "ground_sensors_csv", "ground_sensors", "ground_sensors.csv"),
        ("consumer-credit", "loan_applications_csv", "loan_applications", "loan_applications.csv"),
        ("consumer-credit", "repayment_history_csv", "repayment_history", "repayment_history.csv"),
    ]
    ingested: dict[str, Any] = {}
    for domain, connector, dataset, filename in plan:
        meta = ingest_sample(engine, domain=domain, connector=connector, dataset=dataset, filename=filename)
        ingested[f"{domain}/{dataset}"] = meta
        rec = meta.provenance[-1]
        print(
            f"  [{domain:<17}] {dataset:<20} rows={meta.row_count:<6} "
            f"checksum={(rec.checksum_sha256 or '')[:12]}… sig={rec.signature_alg}"
        )
        assert meta.row_count > 0
        assert rec.content_signature, "provenance signature must be attached at capture"

    climate_ds = ingested["climate-emissions/facility_emissions"]
    credit_apps = ingested["consumer-credit/loan_applications"]

    # ---------------------------------------------------------------- #
    # 3) Governed aggregate on CLIMATE (open data) -> carbon-aware region.
    # ---------------------------------------------------------------- #
    _rule("3) GOVERNED QUERY — climate (open data), carbon-aware placement")
    climate_spec = QuerySpec(
        sql=(
            "SELECT count(*) AS readings, "
            "round(sum(co2e_tonnes), 1) AS total_co2e_tonnes "
            "FROM facility_emissions"
        ),
        datasets=[climate_ds.ref],
        purpose="public-emissions-report",
    )
    t0 = time.perf_counter()
    climate_result = engine.query(climate_spec)  # anonymous public principal
    climate_latency_ms = (time.perf_counter() - t0) * 1000.0
    _kv("result", climate_result.rows[0])
    _kv("engine", climate_result.stats.engine)
    _kv("region chosen", climate_result.stats.region)
    _kv("energy (kWh)", f"{climate_result.stats.energy_kwh:.3e}")
    _kv("carbon (gCO2)", f"{climate_result.stats.carbon_g:.6f}")
    greenest = min(engine.carbon_snapshot(), key=lambda r: r.gco2_per_kwh)
    _kv("greenest region", f"{greenest.region} @ {greenest.gco2_per_kwh:.0f} gCO2/kWh")
    assert climate_result.stats.region == greenest.region, "scheduler must pick the greenest region"
    assert climate_result.stats.carbon_g > 0

    # ---------------------------------------------------------------- #
    # 4a) Governed aggregate on CONSUMER-CREDIT with differential privacy.
    #     Same engine machinery (scheduler.execute) enforcing the manifest's
    #     differential_privacy + mask obligations on real credit data.
    # ---------------------------------------------------------------- #
    _rule("4a) GOVERNED QUERY — consumer-credit aggregate UNDER differential privacy")
    credit_loc = engine.lakehouse.table_location(credit_apps.ref)
    credit_spec = QuerySpec(
        sql=(
            "SELECT decision, count(*) AS n, round(avg(income), 2) AS avg_income "
            "FROM loan_applications GROUP BY decision ORDER BY decision"
        ),
        datasets=[credit_apps.ref],
        purpose="portfolio-analyst",
    )
    dp_obligations = [
        Obligation(kind="differential_privacy", params={"epsilon": 1.0, "delta": 1e-6, "mechanism": "laplace"}),
        Obligation(kind="mask", params={"fields": credit_apps.schema_.pii_fields, "strategy": "hash"}),
    ]
    t0 = time.perf_counter()
    credit_result = engine.scheduler.execute(credit_spec, {"loan_applications": credit_loc}, obligations=dp_obligations)
    credit_latency_ms = (time.perf_counter() - t0) * 1000.0
    print("  DP-noised group aggregates (counts/incomes carry calibrated Laplace noise):")
    for row in credit_result.rows:
        print(f"    decision={row['decision']:<9} n≈{row['n']:<6} avg_income≈{row['avg_income']}")
    _kv("dp applied", credit_result.stats.dp_applied)
    _kv("epsilon spent", credit_result.stats.epsilon_spent)
    budget = engine.governance.budget("portfolio-analyst", credit_apps.ref)
    _kv("privacy budget", f"spent={budget.spent} / epsilon={budget.epsilon} (remaining={budget.remaining})")
    assert credit_result.stats.dp_applied and credit_result.stats.epsilon_spent > 0

    # Show that PII columns never leak even when projected: masking redacts them.
    raw_pii = engine.lakehouse.scan(credit_apps.ref, columns=["email"]).slice(0, 3)
    masked = engine.governance.apply_obligations(
        raw_pii,
        [Obligation(kind="mask", params={"fields": ["email"], "strategy": "hash"})],
        schema=credit_apps.schema_,
    )
    print("  PII masking on projection (email column):")
    print(f"    raw    : {raw_pii.column('email').to_pylist()}")
    print(f"    masked : {masked.column('email').to_pylist()}")
    assert all("@" not in v for v in masked.column("email").to_pylist())

    # ---------------------------------------------------------------- #
    # 4b) Raw PII SELECT on consumer-credit is DENIED by governance.
    # ---------------------------------------------------------------- #
    _rule("4b) GOVERNANCE DENY — raw row-level PII SELECT on consumer-credit")
    analyst = Principal(
        subject="analyst-1",
        roles=["analyst"],
        jurisdiction="EU",
        attributes={"region": "EU", "purpose": "analytics"},
    )
    raw_spec = QuerySpec(
        sql="SELECT application_id, applicant_name, national_id, email FROM loan_applications LIMIT 10",
        datasets=[credit_apps.ref],
        purpose="raw-pii-pull",
    )
    try:
        engine.query(raw_spec, analyst)
        raise SystemExit("SECURITY FAILURE: raw PII SELECT was NOT denied")
    except AccessDenied as exc:
        _kv("engine.query verdict", "DENIED")
        _kv("reason", str(exc))

    # And the governance service denies the raw read directly, too.
    meta = engine.catalog.get(credit_apps.ref)
    decision = engine.governance.authorize(
        AccessRequest(principal=analyst, dataset=credit_apps.ref, action=Action.READ, purpose="raw-pii-pull"),
        meta,
    )
    _kv("governance.authorize", f"allow={decision.allow} ({decision.reason})")
    assert not decision.allow

    # ---------------------------------------------------------------- #
    # 5) Lineage + C2PA-style signature verification.
    # ---------------------------------------------------------------- #
    _rule("5) PROVENANCE — lineage graph + C2PA-style signature verification")
    edges = engine.catalog.lineage(climate_ds.ref)
    print("  Lineage edges for climate facility_emissions:")
    for edge in edges:
        print(f"    {edge.src.name}  --{edge.operation}-->  {edge.dst.name}")
    assert edges, "ingest must record a lineage edge"

    chain = engine.provenance.chain(climate_ds.ref)
    capture = chain[-1]
    _kv("capture record", f"by={capture.captured_by} method={capture.method} alg={capture.signature_alg}")
    # Verify a signed asset round-trip with the same signer the engine uses.
    facility_ids = engine.lakehouse.scan(climate_ds.ref, columns=["facility_id"]).column("facility_id").to_pylist()
    payload = "\n".join(str(v) for v in facility_ids).encode("utf-8")
    signed = engine.provenance.sign_asset(payload, ProvenanceRecord(source_uri=str(climate_ds.ref)))
    verdict = engine.provenance.verify_asset(payload, signed)
    _kv("signature valid", verdict["valid"])
    _kv("checksum match", verdict["checksum_match"])
    # Tampering must break verification.
    tampered = engine.provenance.verify_asset(payload + b"!", signed)
    _kv("tamper rejected", not tampered["valid"])
    assert verdict["valid"] and not tampered["valid"]

    # ---------------------------------------------------------------- #
    # 6) KPI summary table.
    # ---------------------------------------------------------------- #
    _rule("6) KPI SUMMARY")
    quality = {
        ref: round(meta.quality_score, 3) if meta.quality_score else _quality(engine, meta)
        for ref, meta in ingested.items()
    }
    header = f"  {'dataset':<40}{'rows':>8}{'quality':>9}{'carbon_g/q':>13}{'latency_ms':>12}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    _print_kpi("climate-emissions/facility_emissions", ingested["climate-emissions/facility_emissions"],
               quality, climate_result.stats.carbon_g, climate_latency_ms)
    _print_kpi("consumer-credit/loan_applications", ingested["consumer-credit/loan_applications"],
               quality, credit_result.stats.carbon_g, credit_latency_ms)
    for ref in ("climate-emissions/ground_sensors", "consumer-credit/repayment_history"):
        _print_kpi(ref, ingested[ref], quality, None, None)

    _rule("DEMO COMPLETE — one core, two markets, governed + carbon-aware + provenanced")
    print(f"  Throwaway warehouse: {workdir}")


def _quality(engine: AegoriaEngine, meta: Any) -> float:
    """Evaluate the pack-declared quality rules for a dataset's sample."""
    pack = engine.domain_packs.get(meta.ref.domain)
    spec = pack.dataset(meta.ref.name) if pack else None
    if spec is None or not spec.quality_rules:
        return 0.0
    data = engine.lakehouse.scan(meta.ref)
    report = engine.governance.evaluate_quality(meta, data, spec.quality_rules)
    return round(report.score, 3)


def _print_kpi(ref: str, meta: Any, quality: dict[str, float], carbon: Optional[float], latency: Optional[float]) -> None:
    c = "—" if carbon is None else f"{carbon:.6f}"
    lat = "—" if latency is None else f"{latency:.1f}"
    print(f"  {ref:<40}{meta.row_count:>8}{quality.get(ref, 0.0):>9}{c:>13}{lat:>12}")


if __name__ == "__main__":
    main()
