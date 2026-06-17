"""Built-in *lite* reference services.

Importing this package runs the ``@service`` registrations for the complete set
of engine capabilities (lakehouse, ingestion, catalog, governance, scheduler,
knowledge graph, ML, provenance). The engine resolves them by capability + name;
it never imports these modules directly.
"""

from __future__ import annotations

from . import (  # noqa: F401  (import side-effects perform registration)
    catalog,
    governance,
    ingestion,
    knowledge_graph,
    lakehouse,
    ml,
    provenance,
    scheduler,
)

__all__ = [
    "catalog",
    "governance",
    "ingestion",
    "knowledge_graph",
    "lakehouse",
    "ml",
    "provenance",
    "scheduler",
]
