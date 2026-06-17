"""``iceberg`` lakehouse service — open-table-format storage, schema-on-read.

Sits on top of the catalog + storage adapters and offers the
:class:`~aegoria_core.contracts.services.LakehouseService` surface the rest of
the engine uses: create a table from FAIR metadata, append/overwrite Arrow data,
scan it back with column projection and a predicate, resolve a table's physical
location, and list snapshots for time-travel. One Iceberg namespace per domain
keeps markets isolated.
"""

from __future__ import annotations

from typing import Any, Optional

import pyarrow as pa
import structlog

from ..contracts.models import DatasetMetadata, DatasetRef
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.lakehouse")


class IcebergLakehouse:
    """Iceberg-backed lakehouse over the configured catalog + storage adapters."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx

    @property
    def _catalog(self) -> Any:
        return self._ctx.adapter("catalog")

    # -- LakehouseService ----------------------------------------------- #
    def create_table(self, meta: DatasetMetadata) -> str:
        """Create the domain namespace + Iceberg table, returning its location."""
        ref = meta.ref
        self._catalog.create_namespace(ref.domain)
        location = self._catalog.create_table(ref, meta.schema_, location="")
        log.info("create_table", ref=ref.id, location=location)
        return location

    def write(self, ref: DatasetRef, data: pa.Table, mode: str = "append") -> int:
        table = self._catalog.load_table(ref)
        # Align the Arrow schema to the table schema so appends are accepted.
        arrow = self._coerce(table, data)
        if mode == "overwrite":
            table.overwrite(arrow)
        else:
            table.append(arrow)
        log.info("write", ref=ref.id, mode=mode, rows=arrow.num_rows)
        return arrow.num_rows

    def scan(
        self,
        ref: DatasetRef,
        columns: Optional[list[str]] = None,
        predicate: Optional[str] = None,
    ) -> pa.Table:
        table = self._catalog.load_table(ref)
        scan = table.scan(row_filter=predicate) if predicate else table.scan()
        if columns:
            scan = scan.select(*columns)
        return scan.to_arrow()

    def table_location(self, ref: DatasetRef) -> str:
        table = self._catalog.load_table(ref)
        return table.location()

    def snapshots(self, ref: DatasetRef) -> list[dict[str, Any]]:
        table = self._catalog.load_table(ref)
        out: list[dict[str, Any]] = []
        for snap in table.snapshots():
            out.append(
                {
                    "snapshot_id": snap.snapshot_id,
                    "parent_id": snap.parent_snapshot_id,
                    "timestamp_ms": snap.timestamp_ms,
                    "operation": getattr(snap.summary, "operation", None).value
                    if snap.summary and getattr(snap.summary, "operation", None)
                    else None,
                    "summary": dict(snap.summary.additional_properties) if snap.summary else {},
                }
            )
        return out

    # -- helpers -------------------------------------------------------- #
    @staticmethod
    def _coerce(table: Any, data: pa.Table) -> pa.Table:
        """Cast the incoming Arrow table to the table's expected pyarrow schema."""
        try:
            target = table.schema().as_arrow()
        except Exception:  # pragma: no cover - schema introspection best-effort
            return data
        # Reorder/select to the target field order; cast each column to the
        # target field's exact type AND nullability so Iceberg's required/optional
        # contract is satisfied on append.
        arrays = []
        fields = []
        for field in target:
            if field.name in data.column_names:
                col = data.column(field.name)
                if not col.type.equals(field.type):
                    col = col.cast(field.type, safe=False)
                arrays.append(col.combine_chunks() if isinstance(col, pa.ChunkedArray) else col)
                fields.append(field)
        return pa.table(arrays, schema=pa.schema(fields))


@service("lakehouse", "iceberg")
def make_iceberg_lakehouse(*, ctx: EngineContext) -> IcebergLakehouse:
    """Factory the engine invokes to build the Iceberg lakehouse service."""
    return IcebergLakehouse(ctx)
