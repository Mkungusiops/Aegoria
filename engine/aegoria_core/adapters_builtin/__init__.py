"""Built-in *lite* infrastructure adapters.

Importing this package triggers the ``@adapter`` registrations for every
provider the laptop deployment uses. The engine never imports these modules
directly — it resolves them by capability + name from the registry, exactly as
it would resolve an S3 or Kafka adapter shipped by a third party.
"""

from __future__ import annotations

from . import (  # noqa: F401  (import side-effects perform registration)
    carbon_static,
    catalog_sql,
    compute_duckdb,
    identity_static,
    provenance_ed25519,
    storage_localfs,
    stream_inproc,
)

__all__ = [
    "carbon_static",
    "catalog_sql",
    "compute_duckdb",
    "identity_static",
    "provenance_ed25519",
    "storage_localfs",
    "stream_inproc",
]
