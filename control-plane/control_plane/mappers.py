"""Map engine objects -> the console's camelCase JSON view-models.

The engine speaks ``snake_case`` pydantic models (``aegoria_core.contracts.models``);
the console's ``apps/console/lib/types.ts`` speaks ``camelCase``. Every function here
is a pure, total transformation: given whatever the engine actually loaded (which
may be empty until domain-packs are ingested), it returns a valid payload that
matches the corresponding TS interface exactly. Nothing here raises.

Where the engine has authoritative data (datasets, packs, carbon) we use it.
Where the engine has no native concept (pipelines, KPIs, governance proposals,
lineage *products*, overview aggregates) we *derive* sensible values from what is
loaded, so the console always sees a coherent, internally consistent picture.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

# --------------------------------------------------------------------------- #
# Domain-pack presentation hints (purely cosmetic; the console expects a fixed
# enum of accent colors). These are *not* domain logic — they only tint cards.
# --------------------------------------------------------------------------- #
_PACK_COLORS = ("auralis", "pulse", "verdant", "ion", "solar")
_KPI_TONES = ("auralis", "pulse", "verdant", "ion", "solar", "crimson")


def _iso(dt: Any) -> str:
    """Normalize a datetime (or anything) to an ISO-8601 Z string."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(dt, str) and dt:
        return dt
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_choice(key: str, choices: tuple[str, ...]) -> str:
    """Deterministically pick a member of ``choices`` from a string key."""
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return choices[h % len(choices)]


def _enum_value(v: Any) -> Any:
    """Return ``.value`` for enums, else the object unchanged."""
    return getattr(v, "value", v)


# --------------------------------------------------------------------------- #
# Fields & datasets
# --------------------------------------------------------------------------- #
def field_to_json(f: Any) -> dict[str, Any]:
    """``FieldSchema`` -> console ``Field``."""
    sensitivity = _enum_value(getattr(f, "sensitivity", "internal"))
    is_pii = bool(getattr(f, "pii", False)) or sensitivity in ("pii", "phi")
    out: dict[str, Any] = {
        "name": getattr(f, "name", ""),
        "type": _enum_value(getattr(f, "type", "string")),
        "sensitivity": sensitivity,
        "pii": is_pii,
    }
    semantic = getattr(f, "semantic_type", None)
    if semantic:
        out["semanticType"] = semantic
    desc = getattr(f, "description", "")
    if desc:
        out["description"] = desc
    return out


def _pii_field_count(schema: Any) -> int:
    fields = getattr(schema, "fields", []) or []
    count = 0
    for f in fields:
        sens = _enum_value(getattr(f, "sensitivity", "internal"))
        if bool(getattr(f, "pii", False)) or sens in ("pii", "phi"):
            count += 1
    return count


def dataset_to_json(meta: Any) -> dict[str, Any]:
    """``DatasetMetadata`` -> console ``Dataset`` (camelCase)."""
    ref = getattr(meta, "ref", None)
    domain = getattr(ref, "domain", "") if ref else ""
    name = getattr(ref, "name", "") if ref else ""
    dataset_id = ref.id if ref is not None and hasattr(ref, "id") else f"{domain}/{name}"

    schema = getattr(meta, "schema_", None)
    fields = getattr(schema, "fields", []) if schema is not None else []

    jur = getattr(meta, "jurisdiction", None)
    lic = getattr(meta, "license", None)
    fair = getattr(meta, "fair", None)
    provenance = getattr(meta, "provenance", []) or []

    signed = any(
        getattr(p, "content_signature", None) for p in provenance
    )

    return {
        "id": dataset_id,
        "domain": domain,
        "name": name,
        "title": getattr(meta, "title", "") or name,
        "description": getattr(meta, "description", "") or "",
        "modality": _enum_value(getattr(meta, "modality", "structured")),
        "owner": getattr(meta, "owner", "") or "unknown",
        "tags": list(getattr(meta, "tags", []) or []),
        "jurisdiction": getattr(jur, "code", "GLOBAL") if jur else "GLOBAL",
        "regulations": list(getattr(jur, "regulations", []) or []) if jur else [],
        "residencyRequired": bool(getattr(jur, "residency_required", False)) if jur else False,
        "license": getattr(lic, "spdx_id", "CC-BY-4.0") if lic else "CC-BY-4.0",
        "rows": int(getattr(meta, "row_count", 0) or 0),
        "bytes": int(getattr(meta, "byte_size", 0) or 0),
        "qualityScore": float(getattr(meta, "quality_score", 0.0) or 0.0),
        "fair": {
            "findable": bool(getattr(fair, "findable", False)) if fair else False,
            "accessible": bool(getattr(fair, "accessible", False)) if fair else False,
            "interoperable": bool(getattr(fair, "interoperable", False)) if fair else False,
            "reusable": bool(getattr(fair, "reusable", False)) if fair else False,
        },
        "fields": [field_to_json(f) for f in fields],
        "updatedAt": _iso(getattr(meta, "updated_at", None)),
        "signed": bool(signed),
        "piiFields": _pii_field_count(schema) if schema is not None else 0,
    }


# --------------------------------------------------------------------------- #
# Domain packs
# --------------------------------------------------------------------------- #
def pack_to_json(manifest: Any) -> dict[str, Any]:
    """``DomainPackManifest`` -> console ``DomainPack`` (camelCase)."""
    pack_id = getattr(manifest, "id", "")
    modalities = [_enum_value(m) for m in (getattr(manifest, "modalities", []) or [])]
    if not modalities:
        # Derive from declared datasets if the manifest didn't enumerate them.
        seen: list[str] = []
        for ds in getattr(manifest, "datasets", []) or []:
            mod = _enum_value(getattr(ds, "modality", "structured"))
            if mod not in seen:
                seen.append(mod)
        modalities = seen or ["structured"]

    return {
        "id": pack_id,
        "name": getattr(manifest, "name", pack_id),
        "version": getattr(manifest, "version", "0.1.0"),
        "description": getattr(manifest, "description", "") or "",
        "maintainer": getattr(manifest, "maintainer", "") or "",
        "status": "active",
        "modalities": modalities,
        "datasets": len(getattr(manifest, "datasets", []) or []),
        "ontologyTerms": len(getattr(manifest, "ontology", []) or []),
        "qualityRules": sum(
            len(getattr(ds, "quality_rules", []) or [])
            for ds in (getattr(manifest, "datasets", []) or [])
        ),
        "models": len(getattr(manifest, "models", []) or []),
        "policies": len(getattr(manifest, "access_policies", []) or []),
        "coreCompat": getattr(manifest, "core_compat", ">=0.1.0,<1.0.0"),
        "color": _stable_choice(pack_id or "pack", _PACK_COLORS),
    }


# --------------------------------------------------------------------------- #
# Access policies
# --------------------------------------------------------------------------- #
def _obligation_to_str(ob: Any) -> str:
    """Render an obligation spec (dict or Obligation) as a compact label."""
    kind = ob.get("kind") if isinstance(ob, dict) else getattr(ob, "kind", "")
    params = ob.get("params", {}) if isinstance(ob, dict) else getattr(ob, "params", {})
    if not params:
        return str(kind)
    inner = ", ".join(f"{k}={v}" for k, v in params.items())
    return f"{kind}({inner})"


def policy_to_json(domain: str, spec: Any) -> dict[str, Any]:
    """``AccessPolicySpec`` -> console ``AccessPolicy`` (camelCase)."""
    out: dict[str, Any] = {
        "id": getattr(spec, "id", ""),
        "description": getattr(spec, "description", "") or "",
        "effect": getattr(spec, "effect", "allow"),
        "roles": list(getattr(spec, "roles", []) or []),
        "actions": list(getattr(spec, "actions", []) or []),
        "datasets": list(getattr(spec, "datasets", []) or []),
        "obligations": [_obligation_to_str(o) for o in (getattr(spec, "obligations", []) or [])],
        "domain": domain,
    }
    condition = getattr(spec, "condition", None)
    if condition:
        out["condition"] = condition
    return out


# --------------------------------------------------------------------------- #
# Carbon
# --------------------------------------------------------------------------- #
def carbon_to_json(reading: Any) -> dict[str, Any]:
    """``CarbonReading`` -> console ``CarbonReading`` (camelCase)."""
    return {
        "region": getattr(reading, "region", "local"),
        "gco2PerKwh": float(getattr(reading, "gco2_per_kwh", 0.0) or 0.0),
        "renewableFraction": float(getattr(reading, "renewable_fraction", 0.0) or 0.0),
    }


# --------------------------------------------------------------------------- #
# Privacy budgets
# --------------------------------------------------------------------------- #
def budget_to_json(subject: str, dataset_id: str, budget: Any) -> dict[str, Any]:
    """``PrivacyBudget`` -> console ``PrivacyBudget`` (camelCase)."""
    return {
        "subject": subject,
        "dataset": dataset_id,
        "epsilon": float(getattr(budget, "epsilon", 1.0) or 0.0),
        "spent": float(getattr(budget, "spent", 0.0) or 0.0),
    }


# --------------------------------------------------------------------------- #
# Query results & runs
# --------------------------------------------------------------------------- #
def query_result_to_json(result: Any) -> dict[str, Any]:
    """``QueryResult`` -> ``{columns, rows, stats}`` with camelCase stats."""
    stats = getattr(result, "stats", None)
    return {
        "columns": list(getattr(result, "columns", []) or []),
        "rows": list(getattr(result, "rows", []) or []),
        "stats": {
            "rows": int(getattr(stats, "rows", 0) or 0),
            "bytesScanned": int(getattr(stats, "bytes_scanned", 0) or 0),
            "durationMs": float(getattr(stats, "duration_ms", 0.0) or 0.0),
            "engine": getattr(stats, "engine", "duckdb"),
            "region": getattr(stats, "region", "local"),
            "energyKwh": float(getattr(stats, "energy_kwh", 0.0) or 0.0),
            "carbonG": float(getattr(stats, "carbon_g", 0.0) or 0.0),
            "dpApplied": bool(getattr(stats, "dp_applied", False)),
            "epsilonSpent": float(getattr(stats, "epsilon_spent", 0.0) or 0.0),
        }
        if stats is not None
        else {},
    }


def query_run_to_json(run_id: str, sql: str, principal: str, domain: str, result: Any,
                      at: Optional[datetime] = None) -> dict[str, Any]:
    """Build a console ``QueryRun`` from an executed ``QueryResult``."""
    stats = getattr(result, "stats", None)
    return {
        "id": run_id,
        "sql": sql,
        "principal": principal,
        "domain": domain,
        "engine": getattr(stats, "engine", "duckdb") if stats else "duckdb",
        "region": getattr(stats, "region", "local") if stats else "local",
        "rows": int(getattr(stats, "rows", 0) or 0) if stats else 0,
        "bytesScanned": int(getattr(stats, "bytes_scanned", 0) or 0) if stats else 0,
        "durationMs": float(getattr(stats, "duration_ms", 0.0) or 0.0) if stats else 0.0,
        "carbonG": float(getattr(stats, "carbon_g", 0.0) or 0.0) if stats else 0.0,
        "dpApplied": bool(getattr(stats, "dp_applied", False)) if stats else False,
        "epsilonSpent": float(getattr(stats, "epsilon_spent", 0.0) or 0.0) if stats else 0.0,
        "at": _iso(at),
        "status": "ok",
    }


# --------------------------------------------------------------------------- #
# Knowledge graph
# --------------------------------------------------------------------------- #
def entity_to_json(entity: Any, x: float, y: float) -> dict[str, Any]:
    """``Entity`` -> console ``GraphEntity`` (with layout coordinates)."""
    return {
        "id": getattr(entity, "id", ""),
        "label": getattr(entity, "properties", {}).get("label")
        or getattr(entity, "id", ""),
        "type": getattr(entity, "type", ""),
        "domain": getattr(entity, "domain", ""),
        "x": round(float(x), 4),
        "y": round(float(y), 4),
    }


def relation_to_json(relation: Any) -> dict[str, Any]:
    """``Relation`` -> console ``GraphRelation``."""
    return {
        "from": getattr(relation, "src", ""),
        "to": getattr(relation, "dst", ""),
        "type": getattr(relation, "type", ""),
    }


def lineage_edge_to_json(edge: Any) -> dict[str, Any]:
    """``LineageEdge`` -> console ``LineageEdge`` ({from, to, operation})."""
    src = getattr(edge, "src", None)
    dst = getattr(edge, "dst", None)
    src_id = src.id if src is not None and hasattr(src, "id") else str(src)
    dst_id = dst.id if dst is not None and hasattr(dst, "id") else str(dst)
    return {
        "from": src_id,
        "to": dst_id,
        "operation": getattr(edge, "operation", "transform"),
    }


def lineage_node_for_dataset(meta: Any) -> dict[str, Any]:
    """Project a dataset into a lineage *node*."""
    ref = getattr(meta, "ref", None)
    node_id = ref.id if ref is not None and hasattr(ref, "id") else ""
    return {
        "id": node_id,
        "label": getattr(ref, "name", "") if ref else "",
        "kind": "dataset",
        "domain": getattr(ref, "domain", "") if ref else "",
    }


# --------------------------------------------------------------------------- #
# Helpers exported for app.py aggregate derivations
# --------------------------------------------------------------------------- #
def deterministic_unit(key: str) -> float:
    """A stable pseudo-random float in [0, 1) derived from ``key`` — used to give
    derived metrics (pipeline throughput, layout) reproducible variety without
    real telemetry."""
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    return (h % 10_000) / 10_000.0


def unique(seq: Iterable[str]) -> list[str]:
    out: list[str] = []
    for s in seq:
        if s not in out:
            out.append(s)
    return out
