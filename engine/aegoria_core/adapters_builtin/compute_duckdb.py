"""``duckdb`` compute adapter — the embedded query engine for the lite lakehouse.

Exposes each dataset in a :class:`QuerySpec` as a DuckDB view over its Iceberg
data files (``<location>/data/**/*.parquet``), runs the SQL, and returns an Arrow
table plus :class:`QueryStats`. The adapter advertises a set of *regions* (taken
from the configured carbon intensities) so the carbon-aware scheduler can pick
where to run; DuckDB itself is local, but a region is a placement label the same
adapter contract supports for Spark/Trino in scale-out.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog

from ..config import AegoriaConfig
from ..contracts.models import QuerySpec, QueryStats
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.compute.duckdb")


def _data_glob(location: str) -> str:
    """Build a recursive parquet glob under an Iceberg table location."""
    path = location[len("file://"):] if location.startswith("file://") else location
    return str(Path(path) / "data" / "**" / "*.parquet")


def _scanned_bytes(location: str) -> int:
    path = location[len("file://"):] if location.startswith("file://") else location
    data_dir = Path(path) / "data"
    total = 0
    if data_dir.exists():
        for f in data_dir.rglob("*.parquet"):
            try:
                total += f.stat().st_size
            except OSError:
                continue
    return total


class DuckDBCompute:
    """Runs SQL over lakehouse tables using an in-process DuckDB connection."""

    name = "duckdb"

    def __init__(self, regions: list[str]) -> None:
        # Regions are placement labels; DuckDB executes locally regardless.
        self.regions: list[str] = regions or ["local"]

    def _connect(self) -> Any:
        import duckdb

        con = duckdb.connect(database=":memory:")
        return con

    def _register_views(self, con: Any, table_paths: dict[str, str]) -> int:
        bytes_scanned = 0
        for name, location in table_paths.items():
            glob = _data_glob(location)
            raw = location[len("file://"):] if location.startswith("file://") else location
            data_dir = Path(raw) / "data"
            has_data = data_dir.exists() and any(data_dir.rglob("*.parquet"))
            if has_data:
                con.execute(
                    f'CREATE OR REPLACE VIEW "{name}" AS '
                    f"SELECT * FROM read_parquet('{glob}', union_by_name=true)"
                )
            else:
                # Empty table: register an empty result so queries don't crash.
                con.execute(f'CREATE OR REPLACE VIEW "{name}" AS SELECT NULL WHERE 1=0')
            bytes_scanned += _scanned_bytes(location)
        return bytes_scanned

    # -- ComputeAdapter ------------------------------------------------- #
    def execute(self, spec: QuerySpec, table_paths: dict[str, str]) -> tuple[Any, QueryStats]:
        if not spec.sql:
            raise ValueError("duckdb compute adapter requires spec.sql")
        con = self._connect()
        try:
            bytes_scanned = self._register_views(con, table_paths)
            start = time.perf_counter()
            sql = spec.sql
            if spec.limit is not None and "limit" not in sql.lower():
                sql = f"SELECT * FROM ({sql}) AS _q LIMIT {int(spec.limit)}"
            result = con.execute(sql)
            # ``to_arrow_table`` materializes a pa.Table (``.arrow()`` returns a
            # streaming RecordBatchReader on this DuckDB version).
            table = result.to_arrow_table()
            duration_ms = (time.perf_counter() - start) * 1000.0
        finally:
            con.close()
        stats = QueryStats(
            rows=table.num_rows,
            bytes_scanned=bytes_scanned,
            duration_ms=round(duration_ms, 3),
            engine="duckdb",
            region=self.regions[0],
        )
        log.debug("execute", rows=stats.rows, bytes=stats.bytes_scanned, ms=stats.duration_ms)
        return table, stats

    def estimate(self, spec: QuerySpec, table_paths: dict[str, str]) -> QueryStats:
        bytes_scanned = sum(_scanned_bytes(loc) for loc in table_paths.values())
        # Cheap heuristic: ~1ms per MiB scanned, floor of 1ms.
        est_ms = max(1.0, bytes_scanned / (1024 * 1024))
        return QueryStats(
            rows=0,
            bytes_scanned=bytes_scanned,
            duration_ms=round(est_ms, 3),
            engine="duckdb",
            region=self.regions[0],
        )


@adapter("compute", "duckdb")
def make_duckdb_compute(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> DuckDBCompute:
    """Factory the engine invokes to build the DuckDB compute adapter.

    Regions come from the configured carbon intensities so the scheduler has a
    set of placements to choose the greenest one from.
    """
    regions = list(config.carbon.intensities.keys())
    return DuckDBCompute(regions)
