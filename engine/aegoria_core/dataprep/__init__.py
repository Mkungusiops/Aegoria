"""Aegoria data-prep — connect any source, assess it, clean it, ship it (incl. AI-ready).

This whole capability is *additive*: it registers a ``dataprep`` provider and the
``source`` connectors through the registry and reuses the engine's governance,
lakehouse and provenance services. Importing it runs those registrations; the
frozen engine core is never edited.

Public surface::

    from aegoria_core.dataprep import get_studio
    studio = get_studio(engine)
    report = studio.assess("data.csv")
    result = studio.onboard("mydb.sqlite", dataset="customers")
"""

from __future__ import annotations

from typing import Any

from . import ai_export, cleanser, profiler, studio  # noqa: F401  (registration side-effects)
from .models import (
    AiBundle,
    AssessmentReport,
    CleaningPlan,
    CleaningStep,
    CleanResult,
    ColumnProfile,
    OnboardResult,
)
from .studio import DataPrepStudio

__all__ = [
    "AiBundle",
    "AssessmentReport",
    "CleaningPlan",
    "CleaningStep",
    "CleanResult",
    "ColumnProfile",
    "DataPrepStudio",
    "OnboardResult",
    "get_studio",
]


def get_studio(engine: Any) -> DataPrepStudio:
    """Resolve the data-prep studio for a bootstrapped engine (registry-built)."""
    return engine.ctx.registry.adapter(
        "dataprep", "studio", ctx=engine.ctx, config=engine.config
    )
