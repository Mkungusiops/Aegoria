"""Built-in *source* connectors — bring-your-own database/files.

Importing this package runs the ``@adapter("source", ...)`` registrations for the
file, SQLite and SQL connectors. The engine resolves them by name from the
registry, exactly as it resolves storage or compute adapters; a new source type
is added by shipping another adapter, with no engine change.
"""

from __future__ import annotations

from . import (  # noqa: F401  (import side-effects perform registration)
    source_file,
    source_sql,
    source_sqlite,
)
from .base import SourceColumn, SourceConnector, SourceDataset, detect_connector, local_path

__all__ = [
    "SourceColumn",
    "SourceConnector",
    "SourceDataset",
    "detect_connector",
    "local_path",
    "source_file",
    "source_sql",
    "source_sqlite",
]
