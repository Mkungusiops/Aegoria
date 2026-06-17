"""Service protocols — the domain-neutral capabilities of the core engine.

A *service* is platform capability (ingest, govern, schedule compute, resolve
entities) that is identical across every market. A service may USE adapters, but
it never encodes domain meaning — that arrives via domain-packs. The engine
resolves services by these protocols, so an implementation can be swapped or
upgraded without the engine knowing the concrete class.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Protocol, runtime_checkable

try:  # pyarrow is a type-only dependency at import time (annotations are stringized)
    import pyarrow as pa  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - provided by the `lite` extra
    pa = None  # type: ignore

from .models import (
    AccessDecision,
    AccessRequest,
    CarbonReading,
    DatasetMetadata,
    DatasetRef,
    Entity,
    LineageEdge,
    Obligation,
    PrivacyBudget,
    ProvenanceRecord,
    QualityReport,
    QualityRule,
    QueryResult,
    QuerySpec,
    Relation,
    TableSchema,
)


@runtime_checkable
class LakehouseService(Protocol):
    """Open-table-format lakehouse (Iceberg/Delta) over object storage — schema-on-read."""

    def create_table(self, meta: DatasetMetadata) -> str: ...
    def write(self, ref: DatasetRef, data: pa.Table, mode: str = "append") -> int:
        """Append/overwrite rows; returns rows written."""
        ...
    def scan(self, ref: DatasetRef, columns: Optional[list[str]] = None, predicate: Optional[str] = None) -> pa.Table: ...
    def table_location(self, ref: DatasetRef) -> str: ...
    def snapshots(self, ref: DatasetRef) -> list[dict[str, Any]]: ...  # time-travel metadata


@runtime_checkable
class IngestionService(Protocol):
    """Unified, multi-modal ingestion. Attaches provenance + lineage at the moment of capture."""

    def ingest(
        self,
        *,
        domain: str,
        connector: str,
        source_uri: str,
        schema: TableSchema,
        options: Optional[dict[str, Any]] = None,
        principal: Optional[str] = None,
    ) -> DatasetMetadata: ...

    def ingest_stream_batch(self, *, domain: str, topic: str, schema: TableSchema, max_records: int = 1000) -> int: ...


@runtime_checkable
class CatalogService(Protocol):
    """FAIR catalog + lineage graph (DataHub / OpenMetadata-backed in scale-out)."""

    def register(self, meta: DatasetMetadata) -> None: ...
    def get(self, ref: DatasetRef) -> Optional[DatasetMetadata]: ...
    def search(self, query: str = "", *, domain: Optional[str] = None, tags: Optional[list[str]] = None) -> list[DatasetMetadata]: ...
    def record_lineage(self, edge: LineageEdge) -> None: ...
    def lineage(self, ref: DatasetRef, depth: int = 3) -> list[LineageEdge]: ...
    def all(self) -> list[DatasetMetadata]: ...


@runtime_checkable
class GovernanceService(Protocol):
    """Trust fabric: PII classification, ABAC/RBAC authorization, obligations, DP budgets."""

    def classify(self, meta: DatasetMetadata, sample: Optional[pa.Table] = None) -> DatasetMetadata:
        """Auto-detect PII/PHI, tag fields, raise sensitivity. Returns updated metadata."""
        ...
    def authorize(self, request: AccessRequest, meta: DatasetMetadata) -> AccessDecision: ...
    def apply_obligations(self, data: pa.Table, obligations: list[Obligation], *, schema: TableSchema) -> pa.Table:
        """Enforce mask/tokenize/aggregate/differential-privacy obligations on query output."""
        ...
    def budget(self, subject: str, ref: DatasetRef) -> PrivacyBudget: ...
    def evaluate_quality(self, meta: DatasetMetadata, data: pa.Table, rules: list[QualityRule]) -> QualityReport: ...


@runtime_checkable
class ComputeScheduler(Protocol):
    """Carbon-aware placement + execution. Picks the greenest capable engine/region."""

    def place(self, spec: QuerySpec, table_paths: dict[str, str]) -> dict[str, Any]:
        """Return chosen {engine, region, estimated_carbon_g, reason}."""
        ...
    def execute(
        self,
        spec: QuerySpec,
        table_paths: dict[str, str],
        obligations: Optional[list[Obligation]] = None,
    ) -> QueryResult:
        """Place on the greenest capable engine, run, then enforce access obligations
        (mask / aggregate / differential privacy) on the result before materializing."""
        ...
    def carbon_snapshot(self) -> list[CarbonReading]: ...


@runtime_checkable
class KnowledgeGraphService(Protocol):
    """Cross-source, cross-sector entity resolution + semantic graph."""

    def upsert_entity(self, entity: Entity) -> str: ...
    def upsert_relation(self, relation: Relation) -> None: ...
    def resolve(self, entity: Entity) -> Entity:
        """Return the canonical entity this one resolves to (entity resolution)."""
        ...
    def neighbors(self, entity_id: str, depth: int = 1) -> tuple[list[Entity], list[Relation]]: ...
    def query(self, pattern: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class MLService(Protocol):
    """Pluggable AI/ML. Models are supplied per-domain; the service stays generic."""

    def register_model(self, domain: str, model_id: str, spec: dict[str, Any]) -> None: ...
    def predict(self, domain: str, model_id: str, data: pa.Table) -> pa.Table: ...
    def detect_anomalies(self, domain: str, ref: DatasetRef, data: pa.Table) -> pa.Table: ...
    def verify_content(self, domain: str, payload: bytes, claims: dict[str, Any]) -> dict[str, Any]:
        """Misinformation / provenance verification: returns {verdict, confidence, evidence}."""
        ...


@runtime_checkable
class ProvenanceService(Protocol):
    """Content signing + verification on top of a ProvenanceSigner (C2PA)."""

    def attach(self, ref: DatasetRef, record: ProvenanceRecord) -> None: ...
    def sign_asset(self, payload: bytes, record: ProvenanceRecord) -> ProvenanceRecord: ...
    def verify_asset(self, payload: bytes, record: ProvenanceRecord) -> dict[str, Any]: ...
    def chain(self, ref: DatasetRef) -> list[ProvenanceRecord]: ...


# Maps a capability name -> the protocol services must satisfy. Used by the
# registry/engine to validate provider wiring without importing concrete classes.
SERVICE_PROTOCOLS: dict[str, type] = {
    "lakehouse": LakehouseService,
    "ingestion": IngestionService,
    "catalog": CatalogService,
    "governance": GovernanceService,
    "scheduler": ComputeScheduler,
    "knowledge_graph": KnowledgeGraphService,
    "ml": MLService,
    "provenance": ProvenanceService,
}
