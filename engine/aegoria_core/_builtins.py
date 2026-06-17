"""Entry-point shim that registers the built-in *lite* providers.

``load()`` is advertised under the ``aegoria.providers`` entry-point group in
``pyproject.toml``. The registry's :func:`load_entrypoints` calls it during
``AegoriaEngine.bootstrap``; importing these packages runs every ``@adapter`` and
``@service`` registration. The engine itself imports nothing concrete.

Each package is imported independently and defensively: a package whose optional
dependency is absent (e.g. ``pyarrow`` on a core-only install) logs and is skipped
rather than aborting registration of the others.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger("aegoria.builtins")

# Ordered so infra adapters and core services register first; the additive
# `source` connectors and `dataprep` capability come last.
_PACKAGES = (
    "aegoria_core.adapters_builtin",
    "aegoria_core.services",
    "aegoria_core.sources",
    "aegoria_core.dataprep",
)


def load() -> None:
    """Import each built-in provider package to trigger its registrations."""
    import importlib

    for name in _PACKAGES:
        try:
            importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - optional-dep resilience
            log.warning("builtin_package_skipped", package=name, error=str(exc))


# Run on import so that merely resolving this entry point (``ep.load()`` imports
# the module before returning the ``load`` attribute) already registers providers.
load()
