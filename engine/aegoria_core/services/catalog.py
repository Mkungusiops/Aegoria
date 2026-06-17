"""``default`` catalog service — a FAIR catalog + lineage graph for the lite engine.

Holds :class:`DatasetMetadata` records and :class:`LineageEdge` edges, persisted
to a small SQLite database under ``<warehouse>/_catalog`` so the control-plane,
CLI and notebooks that share a warehouse all see the same catalog across
processes. ``search`` matches on title/tags/description/domain; ``lineage`` walks
the edge graph breadth-first to a bounded depth. A DataHub/OpenMetadata-backed
service is a drop-in replacement under the same contract.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

import structlog

from ..contracts.models import DatasetMetadata, DatasetRef, LineageEdge
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.catalog")


def _catalog_dir(ctx: EngineContext) -> Path:
    uri = ctx.config.warehouse_uri
    if uri.startswith("file://"):
        uri = uri[len("file://"):]
    path = Path(uri).expanduser() / "_catalog"
    path.mkdir(parents=True, exist_ok=True)
    return path


class DefaultCatalog:
    """SQLite-backed FAIR catalog + lineage graph."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx
        self._lock = threading.RLock()
        self._db_path = _catalog_dir(ctx) / "catalog.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS datasets ("
                " id TEXT PRIMARY KEY, domain TEXT, name TEXT, version TEXT, doc TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS lineage ("
                " src TEXT, dst TEXT, operation TEXT, run_id TEXT, doc TEXT)"
            )
            conn.commit()

    # -- CatalogService ------------------------------------------------- #
    def register(self, meta: DatasetMetadata) -> None:
        doc = meta.model_dump_json(by_alias=True)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO datasets(id, domain, name, version, doc) VALUES(?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET doc=excluded.doc, version=excluded.version",
                (meta.ref.id, meta.ref.domain, meta.ref.name, meta.ref.version, doc),
            )
            conn.commit()
        log.debug("register", ref=meta.ref.id)

    def get(self, ref: DatasetRef) -> Optional[DatasetMetadata]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT doc FROM datasets WHERE id=?", (ref.id,)).fetchone()
        if row is None:
            return None
        return DatasetMetadata.model_validate_json(row["doc"])

    def all(self) -> list[DatasetMetadata]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT doc FROM datasets ORDER BY id").fetchall()
        return [DatasetMetadata.model_validate_json(r["doc"]) for r in rows]

    def search(
        self,
        query: str = "",
        *,
        domain: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[DatasetMetadata]:
        q = query.strip().lower()
        wanted_tags = {t.lower() for t in (tags or [])}
        results: list[DatasetMetadata] = []
        for meta in self.all():
            if domain and meta.ref.domain != domain:
                continue
            meta_tags = {t.lower() for t in meta.tags}
            if wanted_tags and not wanted_tags.issubset(meta_tags):
                continue
            if q:
                haystack = " ".join(
                    [meta.title, meta.description, meta.ref.domain, meta.ref.name, " ".join(meta.tags)]
                ).lower()
                if q not in haystack:
                    continue
            results.append(meta)
        return results

    def record_lineage(self, edge: LineageEdge) -> None:
        doc = edge.model_dump_json()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO lineage(src, dst, operation, run_id, doc) VALUES(?,?,?,?,?)",
                (edge.src.id, edge.dst.id, edge.operation, edge.run_id, doc),
            )
            conn.commit()
        log.debug("record_lineage", src=edge.src.id, dst=edge.dst.id, op=edge.operation)

    def lineage(self, ref: DatasetRef, depth: int = 3) -> list[LineageEdge]:
        """Breadth-first walk of edges touching ``ref`` (both directions)."""
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT doc FROM lineage").fetchall()
        all_edges = [LineageEdge.model_validate_json(r["doc"]) for r in rows]
        seen_nodes = {ref.id}
        collected: list[LineageEdge] = []
        seen_edges: set[str] = set()
        frontier = {ref.id}
        for _ in range(max(0, depth)):
            next_frontier: set[str] = set()
            for edge in all_edges:
                key = f"{edge.src.id}->{edge.dst.id}:{edge.operation}:{edge.run_id}"
                if edge.src.id in frontier or edge.dst.id in frontier:
                    if key not in seen_edges:
                        seen_edges.add(key)
                        collected.append(edge)
                    for node in (edge.src.id, edge.dst.id):
                        if node not in seen_nodes:
                            seen_nodes.add(node)
                            next_frontier.add(node)
            if not next_frontier:
                break
            frontier = next_frontier
        return collected


@service("catalog", "default")
def make_default_catalog(*, ctx: EngineContext) -> DefaultCatalog:
    """Factory the engine invokes to build the default FAIR catalog service."""
    return DefaultCatalog(ctx)
