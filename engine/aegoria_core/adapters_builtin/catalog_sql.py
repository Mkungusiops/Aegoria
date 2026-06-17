"""``sql`` catalog adapter — Iceberg tables tracked in a local SQLite catalog.

Wraps :class:`pyiceberg.catalog.sql.SqlCatalog` so the lakehouse can create
namespaces and tables, append data and time-travel — all on a laptop. The SQLite
file at ``config.catalog_uri`` holds table pointers; the data + manifests live
under ``config.warehouse_uri``. A REST/Glue/Nessie catalog is a drop-in
replacement registered under the same capability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ..config import AegoriaConfig
from ..contracts.models import DatasetRef, FieldType, TableSchema
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.catalog.sql")


def _warehouse_file_uri(config: AegoriaConfig) -> str:
    uri = config.warehouse_uri
    if uri.startswith("file://"):
        path = uri[len("file://"):]
    else:
        path = uri
    abs_path = Path(path).expanduser().resolve()
    abs_path.mkdir(parents=True, exist_ok=True)
    return abs_path.as_uri()


def _iceberg_field_type(ftype: FieldType) -> Any:
    """Map the core :class:`FieldType` vocabulary onto pyiceberg types."""
    from pyiceberg.types import (
        BinaryType,
        BooleanType,
        DateType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        StringType,
        TimestampType,
    )

    mapping = {
        FieldType.STRING: StringType,
        FieldType.INT: IntegerType,
        FieldType.LONG: LongType,
        FieldType.FLOAT: FloatType,
        FieldType.DOUBLE: DoubleType,
        FieldType.BOOL: BooleanType,
        FieldType.DATE: DateType,
        FieldType.TIMESTAMP: TimestampType,
        FieldType.BINARY: BinaryType,
        # Geometry/JSON/array/struct degrade to string for the lite engine.
        FieldType.GEOMETRY: StringType,
        FieldType.JSON: StringType,
        FieldType.ARRAY: StringType,
        FieldType.STRUCT: StringType,
    }
    return mapping.get(ftype, StringType)()


def _to_iceberg_schema(schema: TableSchema) -> Any:
    from pyiceberg.schema import Schema
    from pyiceberg.types import NestedField

    fields = []
    for idx, f in enumerate(schema.fields, start=1):
        fields.append(
            NestedField(
                field_id=idx,
                name=f.name,
                field_type=_iceberg_field_type(f.type),
                required=not f.nullable,
                doc=f.description or None,
            )
        )
    return Schema(*fields)


class SqlCatalogAdapter:
    """Iceberg ``SqlCatalog`` wrapped behind the core ``CatalogAdapter`` protocol."""

    name = "sql"

    def __init__(self, config: AegoriaConfig) -> None:
        from pyiceberg.catalog.sql import SqlCatalog

        # Ensure the directory holding the sqlite catalog file exists.
        cat_uri = config.catalog_uri
        if cat_uri.startswith("sqlite:///"):
            db_path = Path(cat_uri[len("sqlite:///"):]).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._warehouse = _warehouse_file_uri(config)
        self._catalog = SqlCatalog(
            "aegoria",
            uri=config.catalog_uri,
            warehouse=self._warehouse,
        )

    # -- identifier helpers --------------------------------------------- #
    @staticmethod
    def _identifier(ref: DatasetRef) -> str:
        return f"{ref.domain}.{ref.name}"

    # -- CatalogAdapter ------------------------------------------------- #
    def create_namespace(self, namespace: str) -> None:
        if not self._catalog.namespace_exists(namespace):
            self._catalog.create_namespace(namespace)
            log.debug("create_namespace", namespace=namespace)

    def list_namespaces(self) -> list[str]:
        return [".".join(ns) for ns in self._catalog.list_namespaces()]

    def create_table(self, ref: DatasetRef, schema: TableSchema, location: str) -> str:
        self.create_namespace(ref.domain)
        ice_schema = _to_iceberg_schema(schema)
        ident = self._identifier(ref)
        table = self._catalog.create_table_if_not_exists(ident, schema=ice_schema)
        log.debug("create_table", ref=ref.id, location=table.location())
        return table.location()

    def load_table(self, ref: DatasetRef) -> Any:
        return self._catalog.load_table(self._identifier(ref))

    def table_exists(self, ref: DatasetRef) -> bool:
        return self._catalog.table_exists(self._identifier(ref))

    def commit(self, ref: DatasetRef, snapshot: dict[str, Any]) -> None:
        # pyiceberg commits on append/overwrite; this records an explicit
        # property bump so external callers can stamp commit metadata.
        table = self.load_table(ref)
        with table.transaction() as txn:
            txn.set_properties(**{f"aegoria.{k}": str(v) for k, v in snapshot.items()})
        log.debug("commit", ref=ref.id, keys=list(snapshot))

    def list_tables(self, namespace: str) -> list[DatasetRef]:
        refs: list[DatasetRef] = []
        for ident in self._catalog.list_tables(namespace):
            domain, name = ident[-2], ident[-1]
            refs.append(DatasetRef(domain=domain, name=name))
        return refs

    # Convenience accessor for the lakehouse service (kept off the protocol).
    @property
    def pyiceberg(self) -> Any:
        return self._catalog


@adapter("catalog", "sql")
def make_sql_catalog(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> SqlCatalogAdapter:
    """Factory the engine invokes to build the SQL/Iceberg catalog adapter."""
    return SqlCatalogAdapter(config)
