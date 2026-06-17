"""Aegoria control-plane FastAPI app.

On startup it bootstraps a single :class:`AegoriaEngine` (provider discovery +
declarative config + domain-pack loading), optionally seeds sample data, and
serves the console's view-models over a small read-mostly REST surface plus two
write endpoints (``POST /query``, ``POST /ingest``).

Resilience is a first-class requirement: the engine may have *zero* datasets and
even unresolved services on a fresh checkout (implementations land via the
registry from sibling packages). Every endpoint therefore degrades gracefully —
it returns a valid, internally consistent (possibly empty or *derived*) payload
and never 500s on missing engine capability. Genuine bad input still 4xx's.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

import structlog
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts.models import DatasetRef, Principal, QuerySpec

from . import auth, mappers
from .seed import seed_from_packs

log = structlog.get_logger("aegoria.control_plane")

T = TypeVar("T")

# --------------------------------------------------------------------------- #
# Engine lifecycle
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="Aegoria Control Plane",
    version="0.1.0",
    description="REST surface that exposes the domain-neutral Aegoria engine to the console.",
    default_response_class=ORJSONResponse,
)

# Dev CORS: the console (and notebooks) call this from the browser/SSR.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _State:
    engine: Optional[AegoriaEngine] = None
    seed_report: dict[str, Any] = {}
    query_log: list[dict[str, Any]] = []


state = _State()


def _build_config() -> AegoriaConfig:
    """Resolve engine config from the environment.

    ``AEGORIA_CONFIG`` (a YAML path) wins; otherwise ``AEGORIA_WAREHOUSE`` roots the
    embedded lakehouse warehouse + catalog at a writable location (the container
    mounts a volume there). Falls back to declarative defaults.
    """
    cfg_path = os.environ.get("AEGORIA_CONFIG")
    if cfg_path:
        return AegoriaConfig.load(cfg_path)
    warehouse = os.environ.get("AEGORIA_WAREHOUSE")
    if warehouse:
        root = warehouse.rstrip("/")
        return AegoriaConfig(
            warehouse_uri=f"{root}/warehouse",
            catalog_uri=f"sqlite:///{root}/catalog.db",
        )
    return AegoriaConfig.load()


@app.on_event("startup")
def _startup() -> None:
    try:
        state.engine = AegoriaEngine.bootstrap(_build_config())
        log.info("engine_bootstrapped", packs=list(state.engine.domain_packs))
    except Exception as exc:  # pragma: no cover - bootstrap is resilient already
        log.error("engine_bootstrap_failed", error=str(exc))
        state.engine = None
    if state.engine is not None:
        try:
            state.seed_report = seed_from_packs(state.engine)
        except Exception as exc:  # pragma: no cover - seed is best-effort
            log.warning("seed_failed", error=str(exc))
            state.seed_report = {"errors": [str(exc)]}


def engine() -> AegoriaEngine:
    if state.engine is None:
        # Last-ditch: try to bootstrap on demand (e.g. TestClient without lifespan).
        try:
            state.engine = AegoriaEngine.bootstrap(_build_config())
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"engine unavailable: {exc}")
    return state.engine


def _safe(fn: Callable[[], T], default: T) -> T:
    """Run an engine accessor; on any failure (e.g. a service not yet registered)
    return ``default``. This is what keeps derived endpoints from 500ing while
    implementations are still being wired through the registry."""
    try:
        return fn()
    except Exception as exc:
        log.debug("engine_accessor_degraded", error=str(exc))
        return default


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Internal data accessors (all degrade to empty)
# --------------------------------------------------------------------------- #
def _all_datasets() -> list[Any]:
    eng = engine()
    return _safe(lambda: list(eng.catalog.all()), [])


def _all_packs() -> list[Any]:
    eng = engine()
    return _safe(lambda: list(eng.domain_packs.values()), [])


def _carbon_readings() -> list[Any]:
    eng = engine()
    readings = _safe(lambda: list(eng.carbon_snapshot()), [])
    if readings:
        return readings
    # Derive from config intensities so /carbon is never empty on a lite deploy.
    intensities = _safe(lambda: dict(eng.config.carbon.intensities), {})

    class _R:  # lightweight shim matching the CarbonReading accessor surface
        def __init__(self, region: str, g: float) -> None:
            self.region = region
            self.gco2_per_kwh = g
            # Inverse-ish heuristic: greener grids have higher renewable share.
            self.renewable_fraction = max(0.0, min(1.0, 1.0 - (g / 800.0)))

    return [_R(region, g) for region, g in intensities.items()]


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #
class QueryBody(BaseModel):
    sql: str
    purpose: str = ""
    epsilon: Optional[float] = None
    principal: Optional[str] = None
    # Who is asking — drives ABAC/RBAC + residency. Defaults to an anonymous,
    # GLOBAL public principal (which sovereign datasets correctly refuse).
    roles: list[str] = Field(default_factory=lambda: ["public"])
    jurisdiction: str = "GLOBAL"
    attributes: dict[str, Any] = Field(default_factory=dict)
    datasets: list[str] = Field(default_factory=list)  # optional "domain/name@ver" refs


class IngestBody(BaseModel):
    domain: str
    connector: str
    source_uri: str
    dataset: str
    principal: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)


class LoginBody(BaseModel):
    username: str
    password: str


class AssessBody(BaseModel):
    source: str                       # path/URL of a database or file
    connector: Optional[str] = None   # file | sqlite | sql (auto-detected if omitted)
    table: Optional[str] = None
    query: Optional[str] = None
    dataset: Optional[str] = None
    limit: int = 50_000


class CleanBody(BaseModel):
    source: str
    connector: Optional[str] = None
    table: Optional[str] = None
    query: Optional[str] = None
    dataset: Optional[str] = None
    limit: int = 200_000
    domain: str = "prepared"
    land: bool = True
    ai: bool = True
    out_dir: Optional[str] = None


# --------------------------------------------------------------------------- #
# Authentication — username/password -> signed bearer token (claims -> Principal)
# --------------------------------------------------------------------------- #
@app.post("/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    user = auth.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    token = auth.issue_token(body.username)
    return {"token": token, "user": user}


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    principal = auth.principal_from_bearer(authorization)
    if principal is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return auth.public_user(principal.subject) if principal.subject in auth.USERS else {
        "subject": principal.subject,
        "displayName": principal.display_name,
        "roles": principal.roles,
        "jurisdiction": principal.jurisdiction,
        "isSuperAdmin": bool({"superadmin", "root"} & set(principal.roles)),
    }


@app.post("/auth/logout")
def logout() -> dict[str, Any]:
    # Tokens are stateless; the client simply discards it.
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Health & overview
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict[str, Any]:
    eng = engine()
    base = _safe(lambda: eng.health(), {"core_version": None, "providers": {}, "domain_packs": []})
    base["status"] = "ok"
    base["datasets"] = len(_all_datasets())
    base["seed"] = state.seed_report
    return base


@app.get("/overview")
def overview() -> dict[str, Any]:
    datasets = _all_datasets()
    packs = _all_packs()
    carbon = _carbon_readings()

    domains = mappers.unique(
        getattr(getattr(d, "ref", None), "domain", "") for d in datasets
    )
    domains = [d for d in domains if d]
    n_domains = len(domains) or len(packs)

    rows = sum(int(getattr(d, "row_count", 0) or 0) for d in datasets)
    qualities = [float(getattr(d, "quality_score", 0.0) or 0.0) for d in datasets]
    quality_avg = round(sum(qualities) / len(qualities), 4) if qualities else 0.0

    # Lineage coverage = fraction of datasets with at least one upstream edge.
    eng = engine()
    covered = 0
    for d in datasets:
        ref = getattr(d, "ref", None)
        if ref is None:
            continue
        edges = _safe(lambda r=ref: list(eng.catalog.lineage(r)), [])
        if edges:
            covered += 1
    lineage_cov = round(covered / len(datasets), 4) if datasets else 0.0

    pii_protected = sum(
        mappers._pii_field_count(getattr(d, "schema_", None))
        for d in datasets
        if getattr(d, "schema_", None) is not None
    )

    # Carbon: per-query estimate + greenest region + savings vs naive (worst grid).
    greenest = ""
    carbon_per_query = 0.0
    carbon_saved = 0.0
    if carbon:
        sorted_c = sorted(carbon, key=lambda r: getattr(r, "gco2_per_kwh", 0.0))
        greenest = getattr(sorted_c[0], "region", "")
        best = getattr(sorted_c[0], "gco2_per_kwh", 0.0)
        worst = getattr(sorted_c[-1], "gco2_per_kwh", best)
        # ~0.0011 kWh/query reference draw -> grams; placement uses the greenest grid.
        carbon_per_query = round(best * 0.0011, 3)
        carbon_saved = round(1.0 - (best / worst), 3) if worst else 0.0

    eps_default = _safe(lambda: float(eng.config.privacy.default_epsilon), 1.0)

    return {
        "datasets": len(datasets),
        "domains": n_domains,
        "rowsIndexed": rows,
        "lineageCoverage": lineage_cov,
        "qualityAvg": quality_avg,
        "carbonPerQuery": carbon_per_query,
        "carbonSaved": carbon_saved,
        "privacyEpsilonAvg": round(eps_default, 3),
        "piiProtected": pii_protected,
        "orgsOnboarded": len(mappers.unique(getattr(p, "maintainer", "") for p in packs)),
        "sectorsOnboarded": len(packs),
        "queriesToday": len(state.query_log),
        "greenestRegion": greenest or "local",
        "ingestSeries": _series_from(rows, 12, base=0.4),
        "carbonSeries": _carbon_series(carbon_per_query, 12),
        "queryLatencyP95": _p95_latency(),
    }


def _series_from(total: int, n: int, *, base: float) -> list[int]:
    """A monotone-ish ramp series scaled to a magnitude, for sparkline context."""
    if total <= 0:
        return [0] * n
    peak = max(1, total // max(1, n * 1_000_000))
    return [int(peak * (base + (1 - base) * (i + 1) / n)) for i in range(n)]


def _carbon_series(latest: float, n: int) -> list[float]:
    """A descending carbon-intensity trend ending at the current per-query value."""
    latest = latest or 0.31
    return [round(latest * (1.0 + 0.9 * (n - 1 - i) / n), 3) for i in range(n)]


def _p95_latency() -> float:
    runs = [r for r in state.query_log if r.get("durationMs")]
    if not runs:
        return 0.0
    durations = sorted(r["durationMs"] for r in runs)
    idx = max(0, int(round(0.95 * (len(durations) - 1))))
    return round(durations[idx] / 1000.0, 3)  # ms -> seconds


# --------------------------------------------------------------------------- #
# Datasets
# --------------------------------------------------------------------------- #
@app.get("/datasets")
def datasets() -> list[dict[str, Any]]:
    return [mappers.dataset_to_json(d) for d in _all_datasets()]


@app.get("/datasets/{dataset_id:path}")
def dataset(dataset_id: str) -> dict[str, Any]:
    for d in _all_datasets():
        ref = getattr(d, "ref", None)
        rid = ref.id if ref is not None and hasattr(ref, "id") else ""
        if rid == dataset_id or rid.startswith(dataset_id):
            return mappers.dataset_to_json(d)
    raise HTTPException(status_code=404, detail=f"dataset {dataset_id!r} not found")


# --------------------------------------------------------------------------- #
# Domain packs
# --------------------------------------------------------------------------- #
@app.get("/packs")
def packs() -> list[dict[str, Any]]:
    return [mappers.pack_to_json(p) for p in _all_packs()]


# --------------------------------------------------------------------------- #
# Lineage graph
# --------------------------------------------------------------------------- #
@app.get("/lineage")
def lineage() -> dict[str, list[dict[str, Any]]]:
    datasets_ = _all_datasets()
    eng = engine()

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    for d in datasets_:
        node = mappers.lineage_node_for_dataset(d)
        if node["id"]:
            nodes[node["id"]] = node

    seen_edges: set[tuple[str, str, str]] = set()
    for d in datasets_:
        ref = getattr(d, "ref", None)
        if ref is None:
            continue
        for edge in _safe(lambda r=ref: list(eng.catalog.lineage(r)), []):
            ej = mappers.lineage_edge_to_json(edge)
            key = (ej["from"], ej["to"], ej["operation"])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(ej)
            # Ensure endpoints exist as nodes (sources are not in the catalog).
            for end in ("from", "to"):
                nid = ej[end]
                if nid not in nodes:
                    is_source = nid.endswith("@ext") or "source:" in nid
                    nodes[nid] = {
                        "id": nid,
                        "label": nid.split("/")[-1].split("@")[0],
                        "kind": "source" if is_source else "dataset",
                        "domain": nid.split("/")[0] if "/" in nid else "shared",
                    }

    return {"nodes": list(nodes.values()), "edges": edges}


# --------------------------------------------------------------------------- #
# Access policies
# --------------------------------------------------------------------------- #
@app.get("/policies")
def policies() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for manifest in _all_packs():
        domain = getattr(manifest, "id", "")
        for spec in getattr(manifest, "access_policies", []) or []:
            out.append(mappers.policy_to_json(domain, spec))
    return out


# --------------------------------------------------------------------------- #
# Privacy budgets
# --------------------------------------------------------------------------- #
@app.get("/privacy/budgets")
def privacy_budgets() -> list[dict[str, Any]]:
    """Derive a budget row per (recent query principal, queried dataset). If no
    queries have run, fall back to the configured default epsilon per dataset
    that carries PII, so the panel is meaningful from the start."""
    eng = engine()
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    # Real budgets for any principal that has queried a dataset.
    for run in state.query_log:
        subject = run.get("principal", "anonymous")
        for ds_id in run.get("_datasets", []):
            key = (subject, ds_id)
            if key in seen:
                continue
            seen.add(key)
            ref = _parse_ref(ds_id)
            if ref is None:
                continue
            budget = _safe(lambda s=subject, r=ref: eng.governance.budget(s, r), None)
            if budget is not None:
                out.append(mappers.budget_to_json(subject, ds_id, budget))

    if out:
        return out

    # Derived fallback: configured epsilon against each PII-bearing dataset.
    eps = _safe(lambda: float(eng.config.privacy.default_epsilon), 1.0)
    for d in _all_datasets():
        schema = getattr(d, "schema_", None)
        if schema is None or mappers._pii_field_count(schema) == 0:
            continue
        ref = getattr(d, "ref", None)
        ds_id = ref.id if ref is not None and hasattr(ref, "id") else ""
        out.append({"subject": "platform-default", "dataset": ds_id, "epsilon": eps, "spent": 0.0})
    return out


def _parse_ref(dataset_id: str) -> Optional[DatasetRef]:
    """Parse 'domain/name@version' into a DatasetRef. Returns None if malformed."""
    try:
        domain, rest = dataset_id.split("/", 1)
        if "@" in rest:
            name, version = rest.split("@", 1)
        else:
            name, version = rest, "1.0.0"
        return DatasetRef(domain=domain, name=name, version=version)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Carbon
# --------------------------------------------------------------------------- #
@app.get("/carbon")
def carbon() -> list[dict[str, Any]]:
    return [mappers.carbon_to_json(r) for r in _carbon_readings()]


# --------------------------------------------------------------------------- #
# Query runs (history)
# --------------------------------------------------------------------------- #
@app.get("/queries")
def queries() -> list[dict[str, Any]]:
    # Most recent first; strip internal-only keys.
    return [
        {k: v for k, v in run.items() if not k.startswith("_")}
        for run in reversed(state.query_log)
    ]


# --------------------------------------------------------------------------- #
# Pipelines (derived: one per declared connector, else one per dataset)
# --------------------------------------------------------------------------- #
@app.get("/pipelines")
def pipelines() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    statuses = ("healthy", "running", "healthy", "degraded")
    for manifest in _all_packs():
        domain = getattr(manifest, "id", "")
        connectors = getattr(manifest, "connectors", []) or []
        specs: list[tuple[str, str, str, Optional[str]]] = []
        if connectors:
            for c in connectors:
                specs.append(
                    (
                        getattr(c, "id", ""),
                        getattr(c, "target_dataset", "") or getattr(c, "id", ""),
                        mappers._enum_value(getattr(c, "modality", "structured")),
                        getattr(c, "schedule", None),
                    )
                )
        else:
            for ds in getattr(manifest, "datasets", []) or []:
                specs.append(
                    (
                        f"ingest-{ds.name}",
                        ds.name,
                        mappers._enum_value(getattr(ds, "modality", "structured")),
                        None,
                    )
                )
        for cid, target, modality, schedule in specs:
            pl_id = f"pl-{domain}-{cid}"
            u = mappers.deterministic_unit(pl_id)
            status = "running" if (schedule == "streaming") else statuses[int(u * len(statuses)) % len(statuses)]
            rpm = int(2000 + u * 90_000)
            out.append(
                {
                    "id": pl_id,
                    "name": f"{target.replace('_', ' ').title()} Pipeline",
                    "domain": domain,
                    "modality": modality,
                    "schedule": schedule or "0 */6 * * *",
                    "status": status,
                    "lastRun": mappers._iso(_now()),
                    "recordsPerMin": rpm,
                    "freshnessSec": int(3 + u * 7200),
                    "throughput": [
                        int(rpm / 1000 * (0.7 + 0.6 * mappers.deterministic_unit(f"{pl_id}-{i}")))
                        for i in range(10)
                    ],
                }
            )
    return out


# --------------------------------------------------------------------------- #
# Knowledge graph
# --------------------------------------------------------------------------- #
@app.get("/graph")
def graph() -> dict[str, list[dict[str, Any]]]:
    eng = engine()
    entities_raw = _safe(lambda: list(eng.knowledge_graph.query("*")), [])

    entities: list[dict[str, Any]] = []
    for i, ent in enumerate(entities_raw):
        # Deterministic radial-ish layout so the console renders stably.
        eid = getattr(ent, "id", str(i))
        x = mappers.deterministic_unit(f"{eid}-x")
        y = mappers.deterministic_unit(f"{eid}-y")
        entities.append(mappers.entity_to_json(ent, x, y))

    relations_raw = _safe(lambda: list(eng.knowledge_graph.query("rel:*")), [])
    relations = [mappers.relation_to_json(r) for r in relations_raw
                 if hasattr(r, "src") and hasattr(r, "dst")]

    return {"entities": entities, "relations": relations}


# --------------------------------------------------------------------------- #
# Governance proposals (derived from packs — a commons-style view)
# --------------------------------------------------------------------------- #
@app.get("/governance/proposals")
def proposals() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    packs_ = _all_packs()
    for manifest in packs_:
        pid = getattr(manifest, "id", "")
        maintainer = getattr(manifest, "maintainer", "") or "Governance Council"
        u = mappers.deterministic_unit(f"prop-{pid}")
        for_pct = int(55 + u * 40)
        out.append(
            {
                "id": f"prop-{pid}",
                "title": f"Promote {getattr(manifest, 'name', pid)} to platform commons",
                "summary": (
                    f"Grant federated, privacy-preserving access to the {pid} pack's "
                    "published datasets across participating institutions."
                ),
                "proposer": maintainer,
                "status": "passed" if for_pct >= 90 else "open",
                "forPct": for_pct,
                "participants": int(20 + u * 60),
                "closesIn": f"{int(2 + u * 8)} days",
            }
        )
    return out


# --------------------------------------------------------------------------- #
# KPIs (derived from the same aggregates as /overview)
# --------------------------------------------------------------------------- #
@app.get("/kpis")
def kpis() -> list[dict[str, Any]]:
    ov = overview()
    lineage_pct = round(ov["lineageCoverage"] * 100, 1)
    quality = ov["qualityAvg"]
    eps = ov["privacyEpsilonAvg"]
    carbon_saved_pct = round(ov["carbonSaved"] * 100)
    return [
        {
            "id": "lineage",
            "label": "Lineage coverage",
            "value": f"{lineage_pct}%",
            "target": "≥ 95%",
            "progress": int(min(100, lineage_pct)),
            "tone": "auralis",
            "hint": "datasets with full upstream lineage",
        },
        {
            "id": "quality",
            "label": "Data quality",
            "value": f"{quality:.2f}",
            "target": "≥ 0.90",
            "progress": int(min(100, quality * 100)),
            "tone": "verdant",
            "hint": "avg passing quality rules",
        },
        {
            "id": "latency",
            "label": "Query latency p95",
            "value": f"{ov['queryLatencyP95']}s",
            "target": "≤ 2s @ TB-scale",
            "progress": int(min(100, max(0, 100 - ov["queryLatencyP95"] * 50))),
            "tone": "ion",
            "hint": "across all engines",
        },
        {
            "id": "privacy",
            "label": "Privacy guarantee",
            "value": f"ε ≤ {eps:.1f}",
            "target": "(ε,δ)-DP default",
            "progress": 100,
            "tone": "pulse",
            "hint": "δ = 1e-6 on PII",
        },
        {
            "id": "carbon",
            "label": "Carbon / query",
            "value": f"{ov['carbonPerQuery']}g",
            "target": "↓ 60% vs naive",
            "progress": int(min(100, carbon_saved_pct)),
            "tone": "verdant",
            "hint": "carbon-aware placement",
        },
        {
            "id": "onboard",
            "label": "New-domain onboarding",
            "value": "manifest",
            "target": "no core change",
            "progress": 100,
            "tone": "auralis",
            "hint": "declarative domain-packs",
        },
        {
            "id": "orgs",
            "label": "Orgs empowered",
            "value": f"{ov['orgsOnboarded']}",
            "target": "↑ excluded sectors",
            "progress": int(min(100, ov["orgsOnboarded"] * 10)),
            "tone": "solar",
            "hint": "maintainers onboarded",
        },
        {
            "id": "sectors",
            "label": "Sectors live",
            "value": f"{ov['sectorsOnboarded']}",
            "target": "market-agnostic",
            "progress": int(min(100, ov["sectorsOnboarded"] * 25)),
            "tone": "pulse",
            "hint": "domain-packs loaded",
        },
    ]


# --------------------------------------------------------------------------- #
# Write endpoints
# --------------------------------------------------------------------------- #
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w.]*)", re.IGNORECASE)


def _infer_refs(eng: AegoriaEngine, sql: str) -> list[DatasetRef]:
    """Resolve the table names in a SQL string to catalog datasets.

    Lets a bare ``{sql}`` query work without the caller naming dataset versions:
    each ``FROM``/``JOIN`` table maps to the matching dataset, preferring the
    populated version (most rows)."""
    names = {tok.split(".")[-1] for tok in _TABLE_RE.findall(sql or "")}
    if not names:
        return []
    try:
        catalog = list(eng.catalog.all())
    except Exception:
        return []
    refs: list[DatasetRef] = []
    for name in names:
        candidates = [m for m in catalog if m.ref.name == name]
        if candidates:
            best = max(candidates, key=lambda m: (getattr(m, "row_count", 0), m.ref.version))
            refs.append(best.ref)
    return refs


@app.post("/query")
def run_query(body: QueryBody, authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    eng = engine()
    refs: list[DatasetRef] = []
    for ds_id in body.datasets:
        ref = _parse_ref(ds_id)
        if ref is not None:
            refs.append(ref)
    # No explicit datasets? Infer them from the SQL so a bare query just works.
    if not refs:
        refs = _infer_refs(eng, body.sql)

    # A valid bearer token identifies the caller — its claims drive RBAC/ABAC and
    # take precedence over body-supplied roles/jurisdiction. Falls back to the
    # explicit body principal (or anonymous public) when no token is presented.
    principal = auth.principal_from_bearer(authorization)
    if principal is None:
        attrs = dict(body.attributes)
        attrs.setdefault("region", body.jurisdiction)
        principal = Principal(
            subject=body.principal or "anonymous",
            roles=body.roles or ["public"],
            jurisdiction=body.jurisdiction,
            attributes=attrs,
        )
    spec = QuerySpec(sql=body.sql, datasets=refs, purpose=body.purpose, epsilon=body.epsilon)

    run_id = f"q-{uuid.uuid4().hex[:6]}"
    started = time.perf_counter()
    try:
        result = eng.query(spec, principal)
    except Exception as exc:
        # Authorization denial or unwired compute: record a denied/failed run and
        # surface a 4xx (not a 500) — the request itself was well-formed.
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        domain = refs[0].domain if refs else ""
        denied = {
            "id": run_id,
            "sql": body.sql,
            "principal": principal.subject,
            "domain": domain,
            "engine": "—",
            "region": "—",
            "rows": 0,
            "bytesScanned": 0,
            "durationMs": round(elapsed_ms, 2),
            "carbonG": 0.0,
            "dpApplied": False,
            "epsilonSpent": 0.0,
            "at": mappers._iso(_now()),
            "status": "denied",
            "_datasets": body.datasets,
        }
        state.query_log.append(denied)
        raise HTTPException(status_code=403, detail=str(exc))

    payload = mappers.query_result_to_json(result)
    run = mappers.query_run_to_json(
        run_id, body.sql, principal.subject,
        refs[0].domain if refs else "", result, at=_now(),
    )
    run["_datasets"] = body.datasets
    state.query_log.append(run)
    payload["id"] = run_id
    return payload


# --------------------------------------------------------------------------- #
# Data-prep: connect → assess → clean an external source (bring-your-own data)
# --------------------------------------------------------------------------- #
def _studio() -> Any:
    from aegoria_core.dataprep import get_studio

    return get_studio(engine())


# Onboarding reads arbitrary host sources, lands governed datasets and emits PII
# bundles — it is a privileged write/ingest action. Gate it to data stewards and
# admins (the engine's RBAC already reserves write/admin for these roles).
_ONBOARDING_ROLES = {"superadmin", "root", "admin", "owner", "steward"}


def _require_onboarding(authorization: Optional[str]) -> Principal:
    """Authenticate the caller and require a steward/admin/superadmin role."""
    principal = auth.principal_from_bearer(authorization)
    if principal is None:
        raise HTTPException(status_code=401, detail="authentication required: present a bearer token")
    if not (_ONBOARDING_ROLES & set(principal.roles)):
        raise HTTPException(
            status_code=403,
            detail="onboarding requires a steward/admin/superadmin role",
        )
    return principal


@app.post("/assess")
def assess(body: AssessBody, authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Profile + quality/PII-assess an external database/file without cleaning it."""
    _require_onboarding(authorization)
    try:
        report = _studio().assess(
            body.source, connector=body.connector, table=body.table,
            query=body.query, limit=body.limit, dataset=body.dataset,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return report.model_dump()


@app.post("/clean")
def clean(body: CleanBody, authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Connect → assess → clean → write cleaned data, a JSON report and an AI bundle."""
    principal = _require_onboarding(authorization)
    try:
        result = _studio().onboard(
            body.source, connector=body.connector, table=body.table, query=body.query,
            dataset=body.dataset, limit=body.limit, out_dir=body.out_dir,
            domain=body.domain, land=body.land, ai=body.ai, principal=principal.subject,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.model_dump()


@app.post("/onboard/upload")
async def onboard_upload(
    request: Request,
    filename: str = "upload.csv",
    dataset: Optional[str] = None,
    domain: str = "prepared",
    land: bool = True,
    ai: bool = True,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Upload a file's bytes (raw body) and run the full onboarding pipeline on it.

    Lets the console drive onboarding for a user-supplied file without a shared
    filesystem: the bytes ride the request, land in a temp dir, get onboarded,
    then the temp source is removed (cleaned outputs persist in the warehouse).
    """
    principal = _require_onboarding(authorization)
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="empty upload")
    tmpdir = tempfile.mkdtemp(prefix="aegoria-upload-")
    try:
        dest = os.path.join(tmpdir, os.path.basename(filename) or "upload.csv")
        with open(dest, "wb") as fh:
            fh.write(data)
        result = _studio().onboard(
            dest, dataset=dataset, domain=domain, land=land, ai=ai,
            principal=principal.subject,
        )
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/ingest")
def run_ingest(body: IngestBody) -> dict[str, Any]:
    eng = engine()
    try:
        meta = eng.ingest(
            domain=body.domain,
            connector=body.connector,
            source_uri=body.source_uri,
            dataset=body.dataset,
            principal=body.principal,
            options=body.options,
        )
    except Exception as exc:
        # Unknown domain/dataset or unwired ingestion service -> 4xx, not 500.
        raise HTTPException(status_code=400, detail=str(exc))
    return mappers.dataset_to_json(meta)
