"""``sql`` source connector — connect to Postgres/MySQL/etc. via a SQLAlchemy URL.

This is the "bring your *live* database" path (e.g. the Supabase Postgres behind a
data app). It degrades gracefully exactly like the scale-out backends: if no
SQLAlchemy driver is installed the adapter still *registers*, and only raises a
clear, actionable error when actually used — so a lite checkout is never blocked
on a database driver it does not need.
"""

from __future__ import annotations

from typing import Any, Optional

import pyarrow as pa
import structlog

from ..registry import adapter
from .base import SourceColumn, SourceDataset

log = structlog.get_logger("aegoria.source.sql")

_MISSING = (
    "the 'sql' source needs SQLAlchemy + a driver (e.g. `pip install sqlalchemy "
    "psycopg[binary]`). Install it, or export the table to CSV/Parquet and use the "
    "'file' connector."
)


class SqlSource:
    """SQLAlchemy-backed reader for live relational databases."""

    name = "sql"

    @staticmethod
    def _engine(uri: str):  # type: ignore[no-untyped-def]
        try:
            from sqlalchemy import create_engine

            # SQLAlchemy 2.x resolves the DBAPI driver eagerly here, so a missing
            # driver/dialect must be caught inside the guard, not just the import.
            return create_engine(_normalize_url(uri))
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dep
            raise RuntimeError(_MISSING) from exc
        except Exception as exc:  # pragma: no cover - unknown dialect, etc.
            from sqlalchemy.exc import NoSuchModuleError

            if isinstance(exc, NoSuchModuleError):
                raise RuntimeError(_MISSING) from exc
            raise

    # -- SourceConnector ------------------------------------------------- #
    def list_tables(self, uri: str) -> list[str]:
        from sqlalchemy import inspect  # local import: optional dep

        eng = self._engine(uri)
        try:
            return sorted(inspect(eng).get_table_names())
        finally:
            eng.dispose()

    def read(
        self,
        uri: str,
        *,
        table: Optional[str] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[pa.Table, SourceDataset]:
        from sqlalchemy import text

        eng = self._engine(uri)
        try:
            target = table or query
            if target is None:
                tables = self.list_tables(uri)
                if not tables:
                    raise ValueError(f"no readable tables at {uri!r}")
                target = tables[0]

            row_estimate = 0
            if query:
                sql = query
            else:
                sql = f'SELECT * FROM "{target}"'
                with eng.connect() as con:
                    row_estimate = int(
                        con.execute(text(f'SELECT COUNT(*) FROM "{target}"')).scalar() or 0
                    )

            with eng.connect() as con:
                result = con.execute(text(sql))
                names = list(result.keys())
                # Enforce the memory cap, peeking one extra row to detect truncation.
                if limit:
                    rows = [list(r) for r in result.fetchmany(int(limit))]
                    has_more = result.fetchone() is not None
                else:
                    rows = [list(r) for r in result.fetchall()]
                    has_more = False

            arrow = _rows_to_arrow(rows, names)
            if not row_estimate:
                row_estimate = arrow.num_rows + (1 if has_more else 0)
            descriptor = SourceDataset(
                connector=self.name,
                uri=_redact(uri),
                table=str(target),
                row_estimate=row_estimate,
                rows_read=arrow.num_rows,
                truncated=has_more or arrow.num_rows < row_estimate,
                columns=[SourceColumn(name=f.name, source_type=str(f.type)) for f in arrow.schema],
            )
            log.info("read", table=target, rows=arrow.num_rows, total=row_estimate)
            return arrow, descriptor
        finally:
            eng.dispose()


def _normalize_url(uri: str) -> str:
    """Map a bare DB URL to the driver Aegoria bundles, so common URLs just work.

    ``postgres(ql)://…`` → ``postgresql+psycopg://…`` (psycopg v3)
    ``mysql://…`` / ``mariadb://…`` → ``mysql+pymysql://…`` (pure-python pymysql)
    ``oracle://…`` → ``oracle+oracledb://…`` (python-oracledb, thin mode)
    A URL that already names a ``+driver`` is left untouched.
    """
    if "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    if "+" in scheme:  # explicit driver already chosen
        return uri
    s = scheme.lower()
    if s in ("postgres", "postgresql"):
        return f"postgresql+psycopg://{rest}"
    if s in ("mysql", "mariadb"):
        return f"mysql+pymysql://{rest}"
    if s == "oracle":
        return f"oracle+oracledb://{rest}"
    return uri


def _rows_to_arrow(rows: list[list[Any]], names: list[str]) -> pa.Table:
    if not names:
        return pa.table({})
    arrays: list[pa.Array] = []
    for i in range(len(names)):
        values = [row[i] for row in rows]
        try:
            arrays.append(pa.array(values))
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays.append(pa.array([None if v is None else str(v) for v in values], pa.string()))
    return pa.Table.from_arrays(arrays, names=names)


_CRED_QS_KEYS = ("password", "passwd", "pwd")


def _redact(uri: str) -> str:
    """Strip credentials from a SQLAlchemy URL before it lands in provenance.

    Masks the userinfo password (``user:pass@host``) using the SQLAlchemy URL
    parser when available, and scrubs credential-bearing query-string params.
    Falls back to a conservative manual mask so a parse failure never leaks.
    """
    masked = uri
    try:
        from sqlalchemy.engine import make_url

        url = make_url(uri)
        if url.password:
            url = url.set(password="***")
        if url.query:
            q = {k: ("***" if k.lower() in _CRED_QS_KEYS else v) for k, v in url.query.items()}
            url = url.set(query=q)
        masked = url.render_as_string(hide_password=False)
    except Exception:  # pragma: no cover - parser unavailable / odd URL
        if "://" in masked and "@" in masked:
            scheme, rest = masked.split("://", 1)
            authority, _, tail = rest.rpartition("@")  # mask up to the LAST '@'
            if authority and ":" in authority:
                user = authority.split(":", 1)[0]
                masked = f"{scheme}://{user}:***@{tail}"
    # Belt-and-suspenders: scrub any leftover password=... in a raw query string.
    import re as _re

    return _re.sub(r"(?i)(password|passwd|pwd)=[^&\s]*", r"\1=***", masked)


@adapter("source", "sql")
def make_sql_source(*, config: Any = None, ctx: Any = None, **options: Any) -> SqlSource:
    """Factory the registry invokes to build the SQL source connector."""
    return SqlSource()
