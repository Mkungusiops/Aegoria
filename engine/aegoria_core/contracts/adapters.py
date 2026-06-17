"""Infrastructure adapter protocols — the seams that make Aegoria provider-agnostic.

Storage, catalog, compute, streaming and identity all sit behind these
protocols. A `local-fs` warehouse and an S3/MinIO warehouse implement the same
``StorageAdapter``; DuckDB and Spark implement the same ``ComputeAdapter``. The
core engine binds to these protocols only, so a new cloud, lake format, broker
or IdP is added by shipping an adapter — never by editing the engine.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Iterator, Optional, Protocol, runtime_checkable

try:  # pyarrow is a type-only dependency at import time (annotations are stringized)
    import pyarrow as pa  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - provided by the `lite` extra
    pa = None  # type: ignore

from .models import (
    CarbonReading,
    DatasetRef,
    Principal,
    ProvenanceRecord,
    QuerySpec,
    QueryStats,
    TableSchema,
)


@runtime_checkable
class StorageAdapter(Protocol):
    """Object/file storage backing the lakehouse warehouse (local-fs, S3, GCS, ABFS)."""

    name: str

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def list(self, prefix: str) -> Iterable[str]: ...
    def uri(self, key: str) -> str: ...
    # Optional signed URL for offline/edge sync; default impls may raise.
    def presign(self, key: str, expires_s: int = 3600) -> str: ...


@runtime_checkable
class CatalogAdapter(Protocol):
    """Table catalog: namespaces + table metadata pointers (Iceberg REST, Nessie, SQL, Glue)."""

    name: str

    def create_namespace(self, namespace: str) -> None: ...
    def list_namespaces(self) -> list[str]: ...
    def create_table(self, ref: DatasetRef, schema: TableSchema, location: str) -> str: ...
    def load_table(self, ref: DatasetRef) -> Any:  # returns an engine-native table handle
        ...
    def table_exists(self, ref: DatasetRef) -> bool: ...
    def commit(self, ref: DatasetRef, snapshot: dict[str, Any]) -> None: ...
    def list_tables(self, namespace: str) -> list[DatasetRef]: ...


@runtime_checkable
class ComputeAdapter(Protocol):
    """Executes SQL / logical plans over lakehouse tables (DuckDB, Spark, Trino, Ray)."""

    name: str
    # Regions this engine can run in, used by the carbon-aware scheduler.
    regions: list[str]

    def execute(self, spec: QuerySpec, table_paths: dict[str, str]) -> tuple[pa.Table, QueryStats]:
        """Run the query; return an Arrow table + execution stats (incl. bytes scanned)."""
        ...

    def estimate(self, spec: QuerySpec, table_paths: dict[str, str]) -> QueryStats:
        """Cheap pre-flight estimate used for carbon/cost-aware placement."""
        ...


@runtime_checkable
class StreamAdapter(Protocol):
    """Pub/sub for real-time ingest (Kafka, Pulsar, Redpanda, in-process)."""

    name: str

    def produce(self, topic: str, key: Optional[str], value: bytes, headers: Optional[dict[str, str]] = None) -> None: ...
    def consume(self, topic: str, group: str, on_message: Callable[[bytes, dict[str, str]], None]) -> None: ...
    def topics(self) -> list[str]: ...
    def poll(self, topic: str, group: str, max_records: int = 100) -> Iterator[tuple[bytes, dict[str, str]]]: ...


@runtime_checkable
class IdentityAdapter(Protocol):
    """Resolves a bearer token into a Principal with ABAC attributes (OIDC, OAuth2, static)."""

    name: str

    def authenticate(self, token: str) -> Principal: ...
    def resolve_attributes(self, subject: str) -> dict[str, Any]: ...


@runtime_checkable
class ProvenanceSigner(Protocol):
    """Cryptographically signs and verifies content + provenance (C2PA, sha256+ed25519)."""

    name: str

    def sign(self, payload: bytes, record: ProvenanceRecord) -> str:
        """Return a detached signature / C2PA manifest digest for the payload."""
        ...

    def verify(self, payload: bytes, signature: str, record: ProvenanceRecord) -> bool: ...


@runtime_checkable
class CarbonSource(Protocol):
    """Supplies live/forecast grid carbon intensity per region (ElectricityMaps, WattTime, static)."""

    name: str

    def intensity(self, region: str) -> CarbonReading: ...
    def regions(self) -> list[str]: ...
