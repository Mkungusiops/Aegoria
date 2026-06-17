"""``sqlite`` source connector — connect to a local SQLite database (stdlib only).

Opens the database **read-only** (``mode=ro``), picks the richest user table when
none is named, and reads rows into Arrow preserving native SQLite types. No extra
dependency: the standard-library ``sqlite3`` module is the whole driver. A
Postgres/MySQL/Snowflake source is the sibling ``sql`` connector — same protocol.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import structlog

from ..registry import adapter
from .base import SourceColumn, SourceDataset, local_path

log = structlog.get_logger("aegoria.source.sqlite")


def _db_path(uri: str) -> Path:
    raw = uri
    if raw.startswith("sqlite:///"):
        raw = raw[len("sqlite:///"):]
    elif raw.startswith("sqlite://"):
        raw = raw[len("sqlite://"):]
    return local_path(raw)


class SqliteSource:
    """Read-only SQLite reader. The cleaning pipeline's database entrypoint."""

    name = "sqlite"

    def _connect(self, uri: str) -> sqlite3.Connection:
        path = _db_path(uri)
        if not path.exists():
            raise FileNotFoundError(f"sqlite database not found: {path}")
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con

    # -- SourceConnector ------------------------------------------------- #
    def list_tables(self, uri: str) -> list[str]:
        con = self._connect(uri)
        try:
            rows = con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            con.close()

    def read(
        self,
        uri: str,
        *,
        table: Optional[str] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[pa.Table, SourceDataset]:
        con = self._connect(uri)
        try:
            target = table or query
            if target is None:
                target = self._richest_table(con)
            if target is None:
                raise ValueError(f"no readable tables in {uri!r}")

            row_estimate = 0
            if query:
                sql = query
            else:
                sql = f'SELECT * FROM "{target}"'
                row_estimate = self._count(con, target)

            cur = con.execute(sql)
            names = [d[0] for d in cur.description] if cur.description else []
            # Enforce the memory cap by fetching at most `limit` rows, then peeking
            # one more to detect (and honestly report) truncation.
            if limit:
                rows = cur.fetchmany(int(limit))
                has_more = cur.fetchone() is not None
            else:
                rows = cur.fetchall()
                has_more = False
            arrow = _rows_to_arrow(rows, names)
            if not row_estimate:
                row_estimate = arrow.num_rows + (1 if has_more else 0)
            descriptor = SourceDataset(
                connector=self.name,
                uri=str(_db_path(uri)),
                table=str(target),
                row_estimate=row_estimate,
                rows_read=arrow.num_rows,
                truncated=has_more or arrow.num_rows < row_estimate,
                columns=[SourceColumn(name=f.name, source_type=str(f.type)) for f in arrow.schema],
            )
            log.info("read", table=target, rows=arrow.num_rows, total=row_estimate)
            return arrow, descriptor
        finally:
            con.close()

    @staticmethod
    def _count(con: sqlite3.Connection, table: str) -> int:
        try:
            return int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        except sqlite3.Error:  # pragma: no cover - defensive
            return 0

    def _richest_table(self, con: sqlite3.Connection) -> Optional[str]:
        """Pick the table/view with the most rows so a bare connect lands on real data."""
        best: Optional[str] = None
        best_n = -1
        rows = con.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (name,) in rows:
            n = self._count(con, name)
            if n > best_n:
                best, best_n = name, n
        return best


def _rows_to_arrow(rows: list[Any], names: list[str]) -> pa.Table:
    """Build an Arrow table from sqlite rows, falling back to string on mixed types.

    Built positionally (``from_arrays``) so duplicate column labels from a custom
    ``query=`` are preserved rather than silently collapsed/overwritten.
    """
    if not names:
        return pa.table({})
    arrays: list[pa.Array] = []
    for i in range(len(names)):
        values = [row[i] for row in rows]
        try:
            arrays.append(pa.array(values))
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            # Mixed/odd types (e.g. SQLite's dynamic typing) -> coerce to string.
            arrays.append(pa.array([None if v is None else str(v) for v in values], pa.string()))
    return pa.Table.from_arrays(arrays, names=names)


@adapter("source", "sqlite")
def make_sqlite_source(*, config: Any = None, ctx: Any = None, **options: Any) -> SqliteSource:
    """Factory the registry invokes to build the SQLite source connector."""
    return SqliteSource()
