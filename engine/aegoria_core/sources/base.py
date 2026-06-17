"""Source-connector contract — the seam for *bringing your own* database/files.

A :class:`SourceConnector` is an infra adapter (capability ``"source"``) that
introspects and reads an *external*, possibly-messy source — a SQLite/Postgres
database, a CSV/Parquet/JSON file or a folder of them — into an Arrow table the
data-prep pipeline can profile and clean. It is the exact mirror of a
``StorageAdapter`` or ``ComputeAdapter``: the engine binds to this protocol, and
a brand-new source type (S3 select, BigQuery, a SaaS export) is added by shipping
another adapter — never by editing engine code.

These types live outside the *frozen* ``contracts.models``/``services``/
``adapters`` on purpose: the whole data-onboarding capability is additive,
registered through the registry like any third-party plugin.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

try:  # pyarrow is provided by the `lite` extra; annotations are stringized.
    import pyarrow as pa  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pa = None  # type: ignore

from pydantic import BaseModel, Field


class SourceColumn(BaseModel):
    """A column as the *source* describes it, before any cleaning/typing."""

    name: str
    source_type: str = "unknown"  # raw declared type (sqlite decl, csv:string, arrow type)


class SourceDataset(BaseModel):
    """What a connector actually pulled, with honest truncation accounting."""

    connector: str
    uri: str
    table: str = ""
    row_estimate: int = 0      # best-effort total rows available at the source
    rows_read: int = 0         # rows actually materialized into the Arrow table
    truncated: bool = False    # rows_read < row_estimate because a limit was hit
    columns: list[SourceColumn] = Field(default_factory=list)


@runtime_checkable
class SourceConnector(Protocol):
    """Connect to and read an external source into Arrow. The cleaning entrypoint."""

    name: str

    def list_tables(self, uri: str) -> list[str]:
        """List addressable tables/files at the source (may be empty for a single file)."""
        ...

    def read(
        self,
        uri: str,
        *,
        table: Optional[str] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple["pa.Table", SourceDataset]:
        """Read (a slice of) the source into an Arrow table + a provenance descriptor."""
        ...


def local_path(uri: str) -> Path:
    """Resolve a ``file://``/bare path to a local filesystem path."""
    raw = uri
    if raw.startswith("file://"):
        raw = raw[len("file://"):]
    return Path(raw).expanduser()


def detect_connector(uri: str, explicit: Optional[str] = None) -> str:
    """Pick a connector name from an explicit hint or the URI shape/extension.

    - ``sqlite``  : ``*.db`` / ``*.sqlite`` / ``sqlite://`` paths
    - ``sql``     : ``postgres(ql)://`` / ``mysql(+driver)://`` SQLAlchemy URLs
    - ``file``    : ``*.csv`` / ``*.parquet`` / ``*.json`` files or a directory
    """
    if explicit:
        return explicit
    low = uri.lower()
    if low.startswith(("postgres://", "postgresql://", "mysql://", "mysql+", "postgresql+")):
        return "sql"
    if low.startswith("sqlite://") or low.endswith((".db", ".sqlite", ".sqlite3")):
        return "sqlite"
    return "file"
