"""Entry-point shim that registers the built-in *lite* providers.

``load()`` is advertised under the ``aegoria.providers`` entry-point group in
``pyproject.toml``. The registry's :func:`load_entrypoints` calls it during
``AegoriaEngine.bootstrap``; importing the two packages runs every ``@adapter``
and ``@service`` registration. The engine itself imports nothing concrete.
"""

from __future__ import annotations

# Module-level imports so that merely resolving this entry point
# (``importlib.metadata`` ``ep.load()`` imports the module before returning the
# ``load`` attribute) already runs every ``@adapter`` / ``@service``
# registration. ``load()`` remains callable for explicit/idempotent use.
import aegoria_core.adapters_builtin  # noqa: F401,E402
import aegoria_core.services  # noqa: F401,E402


def load() -> None:
    """Import the built-in adapter + service packages to trigger registration."""
    import aegoria_core.adapters_builtin  # noqa: F401
    import aegoria_core.services  # noqa: F401
