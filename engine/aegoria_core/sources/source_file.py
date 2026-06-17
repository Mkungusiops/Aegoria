"""``file`` source connector — CSV / Parquet / JSON files (or a folder of them).

CSV is read **all-as-string** (empty cells preserved, not coerced to null) so the
profiler can see the data's true dirtiness: blanks, stray whitespace, mixed
casing, numbers-stored-as-text, inconsistent date formats. Parquet/JSON keep
their native types. A directory is treated as a catalog of tables (one per file).

Swapping in an S3/GCS object source is a different ``source`` adapter under the
same protocol — the engine never changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import structlog

from ..registry import adapter
from .base import SourceColumn, SourceDataset, local_path

log = structlog.get_logger("aegoria.source.file")

_DATA_SUFFIXES = (".csv", ".tsv", ".parquet", ".pq", ".json", ".ndjson", ".jsonl")


class FileSource:
    """Reads tabular files into Arrow, preserving raw text for honest profiling."""

    name = "file"

    # -- SourceConnector ------------------------------------------------- #
    def list_tables(self, uri: str) -> list[str]:
        path = local_path(uri)
        if path.is_dir():
            return sorted(
                p.name for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in _DATA_SUFFIXES
            )
        return [path.name] if path.exists() else []

    def read(
        self,
        uri: str,
        *,
        table: Optional[str] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[pa.Table, SourceDataset]:
        path = local_path(uri)
        if path.is_dir():
            name = table or (self.list_tables(uri) or [""])[0]
            if not name:
                raise FileNotFoundError(f"no tabular files under {path}")
            path = path / name
        if not path.exists():
            raise FileNotFoundError(f"source file not found: {path}")

        fmt = (options or {}).get("format") or path.suffix.lower().lstrip(".")
        if fmt in ("csv", "tsv"):
            arrow, total = _read_csv_capped(path, limit, delimiter="\t" if fmt == "tsv" else ",")
        elif fmt in ("parquet", "pq"):
            arrow, total = _read_parquet_capped(path, limit)
        elif fmt in ("json", "ndjson", "jsonl"):
            arrow, total = _read_json_capped(path, limit)
        else:
            raise ValueError(f"unsupported source format {fmt!r} for {path}")

        descriptor = SourceDataset(
            connector=self.name,
            uri=str(path),
            table=path.stem,
            row_estimate=total,
            rows_read=arrow.num_rows,
            truncated=arrow.num_rows < total,
            columns=[SourceColumn(name=f.name, source_type=str(f.type)) for f in arrow.schema],
        )
        log.info("read", path=str(path), fmt=fmt, rows=arrow.num_rows, total=total)
        return arrow, descriptor


def _read_csv_capped(path: Path, limit: Optional[int], delimiter: str = ",") -> tuple[pa.Table, int]:
    """Stream a CSV as all-string columns, *collecting* at most ``limit`` rows.

    Reads every column as ``string`` (``strings_can_be_null=False`` keeps ``""``
    distinct from a true null) so blanks and formatting issues survive to the
    profiler. Once the cap is hit it stops *collecting* but keeps scanning to the
    end so ``row_estimate``/``truncated`` reflect the true source size (this means
    the file is still fully parsed — a deliberate trade for honest provenance).
    """
    import pyarrow.csv as pacsv

    read_opts = pacsv.ReadOptions(block_size=1 << 20)
    parse_opts = pacsv.ParseOptions(delimiter=delimiter)

    # Pass 1: column names (so we can force every column to string in pass 2).
    probe = pacsv.open_csv(path, read_options=read_opts, parse_options=parse_opts)
    names = list(probe.schema.names)
    probe.close()

    convert = pacsv.ConvertOptions(
        column_types={n: pa.string() for n in names},
        strings_can_be_null=False,
    )
    reader = pacsv.open_csv(
        path, read_options=read_opts, parse_options=parse_opts, convert_options=convert
    )
    batches: list[pa.RecordBatch] = []
    capped: Optional[pa.Table] = None
    total = 0
    cap_hit = False
    try:
        for batch in reader:
            total += batch.num_rows
            if not cap_hit:
                batches.append(batch)
                if limit and total >= limit:
                    cap_hit = True
                    capped = pa.Table.from_batches(batches).slice(0, limit)
                    batches = []  # release; keep counting `total` for honest truncation
    finally:
        reader.close()

    if capped is None:
        capped = (
            pa.Table.from_batches(batches)
            if batches
            else pa.table({n: pa.array([], pa.string()) for n in names})
        )
    return capped, total


def _read_parquet_capped(path: Path, limit: Optional[int]) -> tuple[pa.Table, int]:
    """Stream only enough row-group batches to satisfy ``limit`` (no full load)."""
    import pyarrow.parquet as pq

    with pq.ParquetFile(path) as pf:
        total = pf.metadata.num_rows
        if not limit:
            return pq.read_table(path), total
        batches: list[pa.RecordBatch] = []
        seen = 0
        for batch in pf.iter_batches(batch_size=min(limit, 65_536)):
            batches.append(batch)
            seen += batch.num_rows
            if seen >= limit:
                break
        table = pa.Table.from_batches(batches).slice(0, limit) if batches else pf.schema_arrow.empty_table()
    return table, total


def _read_json_capped(path: Path, limit: Optional[int]) -> tuple[pa.Table, int]:
    import json

    text = path.read_text()
    try:
        data = json.loads(text)
        rows = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    total = len(rows)
    if limit:
        rows = rows[:limit]
    table = pa.Table.from_pylist(rows) if rows else pa.table({})
    return table, total


@adapter("source", "file")
def make_file_source(*, config: Any = None, ctx: Any = None, **options: Any) -> FileSource:
    """Factory the registry invokes to build the file source connector."""
    return FileSource()
