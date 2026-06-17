"""Aegoria core — a domain-neutral, privacy-preserving big-data lakehouse engine.

The public surface is intentionally tiny and stable:

    from aegoria_core import AegoriaEngine, AegoriaConfig
    engine = AegoriaEngine.bootstrap()

Everything market-specific lives in domain-packs; everything infra-specific lives
in adapters. This module re-exports the engine, config, registry and the full
contract vocabulary.
"""

from __future__ import annotations

from . import contracts
from .config import AegoriaConfig
from .engine import CORE_VERSION, AegoriaEngine, EngineContext
from .registry import Registry, adapter, domain_pack, registry, service

__version__ = CORE_VERSION

__all__ = [
    "AegoriaEngine",
    "AegoriaConfig",
    "EngineContext",
    "Registry",
    "registry",
    "adapter",
    "service",
    "domain_pack",
    "contracts",
    "CORE_VERSION",
    "__version__",
]
