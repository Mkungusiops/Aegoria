"""Aegoria control-plane — the REST API that exposes the engine to the console.

The control-plane owns no domain logic and no infra. It is a thin, resilient
adapter from :class:`aegoria_core.AegoriaEngine` (resolved entirely through the
registry + config) to the JSON view-models the console consumes. Honors the core
invariant: this package never imports a concrete adapter, service or domain-pack.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
