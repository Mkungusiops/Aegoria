"""``default`` ingestion service — multi-format capture with provenance at source.

Reads CSV / Parquet / JSON (and drains the in-process stream) into Arrow that
conforms to the declared :class:`TableSchema`, creates the lakehouse table if
needed, writes the data, and builds a :class:`DatasetMetadata` record whose
:class:`ProvenanceRecord` carries a sha256 checksum AND a signer signature
captured at the moment of ingest. FAIR flags, row/byte counts, classification and
optional quality evaluation are all attached before the dataset is registered in
the catalog.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import structlog

from ..contracts.models import (
    DatasetMetadata,
    DatasetRef,
    FairFlags,
    ProvenanceRecord,
    QualityRule,
    TableSchema,
)
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.ingestion")


def _local_path(source_uri: str) -> Path:
    path = source_uri
    if path.startswith("file://"):
        path = path[len("file://"):]
    return Path(path).expanduser()


class DefaultIngestion:
    """Format-aware ingestion that stamps provenance + FAIR metadata at capture."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx

    # -- IngestionService ----------------------------------------------- #
    def ingest(
        self,
        *,
        domain: str,
        connector: str,
        source_uri: str,
        schema: TableSchema,
        options: Optional[dict[str, Any]] = None,
        principal: Optional[str] = None,
    ) -> DatasetMetadata:
        options = options or {}
        table = self._read(connector, source_uri, schema, options)
        table = self._conform(table, schema)
        raw_bytes = self._stable_bytes(table)
        checksum = hashlib.sha256(raw_bytes).hexdigest()

        lakehouse = self._ctx.service("lakehouse")
        catalog = self._ctx.service("catalog")
        # Reuse the version of an already-declared dataset (e.g. one registered by
        # the domain-pack) so ingestion POPULATES that dataset rather than forking a
        # new version. Falls back to an explicit option, then 1.0.0.
        version = options.get("version") or _declared_version(catalog, domain, schema.name) or "1.0.0"
        ref = DatasetRef(domain=domain, name=schema.name, version=version)

        # Provenance attached AT CAPTURE: checksum + cryptographic signature.
        signer = self._ctx.adapter("provenance")
        record = ProvenanceRecord(
            source_uri=source_uri,
            captured_by=principal or "anonymous",
            method="ingest",
            checksum_sha256=checksum,
            software_agent="aegoria-ingestion",
        )
        record.content_signature = signer.sign(raw_bytes, record)
        record.signature_alg = getattr(signer, "alg", signer.name)

        # Build + (lazily) create the table, then write.
        existing = catalog.get(ref)
        meta = existing or DatasetMetadata(
            ref=ref,
            title=schema.name,
            description=schema.description,
            schema=schema,
            modality=schema.modality,
            owner=principal or "unknown",
            location_uri=None,
        )
        if not self._ctx.adapter("catalog").table_exists(ref):
            meta_for_create = meta.model_copy(deep=True)
            meta.location_uri = lakehouse.create_table(meta_for_create)
        else:
            meta.location_uri = lakehouse.table_location(ref)
        rows_written = lakehouse.write(ref, table, mode=options.get("mode", "append"))

        # Classify PII/PHI on a sample (privacy default-on).
        governance = self._ctx.service("governance")
        meta = governance.classify(meta, sample=table.slice(0, min(200, table.num_rows)))

        # FAIR self-assessment now that we have id + provenance + location + schema.
        meta.provenance = [*meta.provenance, record]
        meta.row_count = lakehouse.scan(ref).num_rows
        meta.byte_size = self._table_byte_size(meta.location_uri)
        meta.fair = FairFlags(
            findable=True,
            accessible=True,
            interoperable=any(f.semantic_type for f in schema.fields),
            reusable=bool(meta.license.spdx_id) and bool(meta.provenance),
        )
        meta.updated_at = datetime.now(timezone.utc)

        # Optional quality gate via governance.
        rules = options.get("quality_rules")
        if rules:
            parsed = [QualityRule.model_validate(r) if isinstance(r, dict) else r for r in rules]
            report = governance.evaluate_quality(meta, table, parsed)
            meta.quality_score = report.score

        catalog.register(meta)
        log.info("ingest", ref=ref.id, rows=rows_written, checksum=checksum[:12])
        return meta

    def ingest_stream_batch(
        self, *, domain: str, topic: str, schema: TableSchema, max_records: int = 1000
    ) -> int:
        """Drain up to ``max_records`` JSON messages off the in-process stream."""
        stream = self._ctx.adapter("stream")
        records: list[dict[str, Any]] = []
        for value, _headers in stream.poll(topic, group=f"ingest:{domain}", max_records=max_records):
            try:
                records.append(json.loads(value.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        if not records:
            return 0
        table = pa.Table.from_pylist(records)
        table = self._conform(table, schema)
        ref = DatasetRef(domain=domain, name=schema.name)
        lakehouse = self._ctx.service("lakehouse")
        if not self._ctx.adapter("catalog").table_exists(ref):
            meta = DatasetMetadata(
                ref=ref, title=schema.name, schema=schema, modality=schema.modality
            )
            lakehouse.create_table(meta)
        written = lakehouse.write(ref, table, mode="append")
        log.info("ingest_stream_batch", topic=topic, rows=written)
        return written

    # -- readers -------------------------------------------------------- #
    def _read(
        self, connector: str, source_uri: str, schema: TableSchema, options: dict[str, Any]
    ) -> pa.Table:
        fmt = (options.get("format") or self._infer_format(source_uri)).lower()
        path = _local_path(source_uri)
        if fmt in ("csv",):
            from pyarrow import csv as pacsv

            return pacsv.read_csv(path)
        if fmt in ("parquet", "pq"):
            import pyarrow.parquet as pq

            return pq.read_table(path)
        if fmt in ("json", "ndjson", "jsonl"):
            return self._read_json(path)
        raise ValueError(f"unsupported ingest format {fmt!r} for {source_uri!r}")

    @staticmethod
    def _infer_format(source_uri: str) -> str:
        suffix = Path(source_uri).suffix.lower().lstrip(".")
        return suffix or "csv"

    @staticmethod
    def _read_json(path: Path) -> pa.Table:
        text = path.read_text()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            return pa.Table.from_pylist(data)
        except json.JSONDecodeError:
            # newline-delimited JSON
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            return pa.Table.from_pylist(rows)

    # -- conforming ----------------------------------------------------- #
    @staticmethod
    def _conform(table: pa.Table, schema: TableSchema) -> pa.Table:
        """Project + cast the Arrow table onto the declared schema's field order."""
        arrow_type_map = {
            "string": pa.string(),
            "int": pa.int32(),
            "long": pa.int64(),
            "float": pa.float32(),
            "double": pa.float64(),
            "bool": pa.bool_(),
            "date": pa.date32(),
            "timestamp": pa.timestamp("us"),
            "binary": pa.binary(),
        }
        cols = []
        names = []
        for field in schema.fields:
            target = arrow_type_map.get(field.type.value, pa.string())
            if field.name in table.column_names:
                col = table.column(field.name)
                if not col.type.equals(target):
                    try:
                        col = col.cast(target, safe=False)
                    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
                        col = col.cast(pa.string()).cast(target, safe=False)
            else:
                col = pa.nulls(table.num_rows, type=target)
            cols.append(col)
            names.append(field.name)
        if not names:
            return table
        return pa.table(cols, names=names)

    @staticmethod
    def _stable_bytes(table: pa.Table) -> bytes:
        """Serialize an Arrow table to a deterministic byte buffer for checksums.

        Uses the Arrow IPC stream format so the checksum is reproducible without
        a pandas dependency.
        """
        if table.num_rows == 0:
            return b""
        import pyarrow.ipc as ipc

        sink = pa.BufferOutputStream()
        with ipc.new_stream(sink, table.schema) as writer:
            writer.write_table(table)
        return sink.getvalue().to_pybytes()

    @staticmethod
    def _table_byte_size(location_uri: Optional[str]) -> int:
        if not location_uri:
            return 0
        raw = location_uri[len("file://"):] if location_uri.startswith("file://") else location_uri
        data_dir = Path(raw) / "data"
        if not data_dir.exists():
            return 0
        return sum(f.stat().st_size for f in data_dir.rglob("*.parquet") if f.is_file())


def _declared_version(catalog: Any, domain: str, name: str) -> Optional[str]:
    """Return the version of an already-registered dataset matching domain+name."""
    try:
        for meta in catalog.all():
            if meta.ref.domain == domain and meta.ref.name == name:
                return meta.ref.version
    except Exception:  # pragma: no cover - catalog may be unavailable
        return None
    return None


@service("ingestion", "default")
def make_default_ingestion(*, ctx: EngineContext) -> DefaultIngestion:
    """Factory the engine invokes to build the default ingestion service."""
    return DefaultIngestion(ctx)
