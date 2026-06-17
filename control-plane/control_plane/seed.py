"""Optional seeding helper — populate the lakehouse so the API serves real rows.

This is strictly best-effort and side-effect-tolerant: a fresh checkout may have
no domain-packs, no sample data, or services that are still being wired by other
agents. ``seed_from_packs`` therefore never raises; it returns a structured
report of what it managed to ingest so the caller can log it.

Seeding works purely through the engine's public surface (``engine.ingest`` over
declared connectors / sample data) — it never imports a concrete adapter or
service, honoring the core invariant.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger("aegoria.control_plane.seed")


def _resolve_sample_uri(pack_root: Path | None, sample: str) -> str:
    """Resolve a pack-relative sample path to an absolute file URI/path."""
    p = Path(sample)
    if p.is_absolute() or pack_root is None:
        return str(p)
    return str((pack_root / sample).resolve())


def _pack_root(engine: Any, domain: str) -> Path | None:
    """Best-effort discovery of a pack's directory (for resolving sample paths)."""
    for base in getattr(engine.config, "domain_pack_paths", []) or []:
        candidate = Path(base) / domain
        if candidate.exists():
            return candidate
    return None


def seed_from_packs(engine: Any, *, principal: str | None = None) -> dict[str, Any]:
    """Ingest each loaded pack's declared sample data, where present.

    Returns ``{"ingested": [...], "skipped": [...], "errors": [...]}``. Never raises.
    """
    report: dict[str, Any] = {"ingested": [], "skipped": [], "errors": []}

    if os.environ.get("AEGORIA_SEED", "1") in ("0", "false", "no"):
        report["skipped"].append("seeding disabled via AEGORIA_SEED")
        return report

    packs = {}
    try:
        packs = engine.domain_packs
    except Exception as exc:  # pragma: no cover - defensive
        report["errors"].append(f"domain_packs unavailable: {exc}")
        return report

    for domain, manifest in packs.items():
        root = _pack_root(engine, domain)
        # Index connectors by their target dataset for quick lookup.
        connectors = {
            c.target_dataset: c
            for c in (getattr(manifest, "connectors", []) or [])
            if getattr(c, "target_dataset", "")
        }
        for ds in getattr(manifest, "datasets", []) or []:
            sample = getattr(ds, "sample_data", None)
            connector = connectors.get(ds.name)
            if not sample and connector is None:
                report["skipped"].append(f"{domain}/{ds.name}: no sample_data/connector")
                continue
            # Idempotency: don't re-ingest a dataset that already has rows (e.g.
            # on a restart against a persisted warehouse volume).
            try:
                from aegoria_core.contracts.models import DatasetRef

                version = getattr(manifest, "version", "0.1.0")
                existing = engine.catalog.get(DatasetRef(domain=domain, name=ds.name, version=version))
                if existing is not None and getattr(existing, "row_count", 0) > 0:
                    report["skipped"].append(f"{domain}/{ds.name}: already populated ({existing.row_count} rows)")
                    continue
            except Exception:  # pragma: no cover - catalog may not be ready
                pass

            source_uri = _resolve_sample_uri(root, sample) if sample else ""
            connector_id = getattr(connector, "id", None) or getattr(connector, "adapter", "file") \
                if connector is not None else "file"
            try:
                meta = engine.ingest(
                    domain=domain,
                    connector=connector_id,
                    source_uri=source_uri,
                    dataset=ds.name,
                    principal=principal,
                )
                ref = getattr(meta, "ref", None)
                report["ingested"].append(ref.id if ref is not None and hasattr(ref, "id")
                                          else f"{domain}/{ds.name}")
            except Exception as exc:
                # Ingestion services / connectors may not exist yet — tolerate.
                report["errors"].append(f"{domain}/{ds.name}: {type(exc).__name__}: {exc}")

    log.info(
        "seed_complete",
        ingested=len(report["ingested"]),
        skipped=len(report["skipped"]),
        errors=len(report["errors"]),
    )
    return report
