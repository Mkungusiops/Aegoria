"""Provider registry — the indirection that keeps the core engine closed for modification.

Adapters, services and domain-packs register *factories* here, keyed by
capability + provider name. The engine resolves what `config` selects; it never
imports a concrete implementation. Adding a backend or a market = registering a
new provider, with zero edits to engine code. This is the mechanical guarantee
behind the "core never changes" constraint.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import structlog

from .contracts.services import SERVICE_PROTOCOLS
from .errors import ProtocolViolation, ProviderNotFound

log = structlog.get_logger("aegoria.registry")

# capability -> provider_name -> factory(**kwargs)
Factory = Callable[..., Any]


class Registry:
    """A scoped registry of adapter, service and domain-pack factories."""

    def __init__(self) -> None:
        self._adapters: dict[str, dict[str, Factory]] = {}
        self._services: dict[str, dict[str, Factory]] = {}
        self._domain_packs: dict[str, Factory] = {}

    # -- adapters (infra: storage/catalog/compute/stream/identity/provenance/carbon) --
    def register_adapter(self, capability: str, name: str, factory: Factory) -> None:
        self._adapters.setdefault(capability, {})[name] = factory
        log.debug("registered_adapter", capability=capability, name=name)

    def adapter(self, capability: str, name: str, **kwargs: Any) -> Any:
        try:
            factory = self._adapters[capability][name]
        except KeyError as exc:
            raise ProviderNotFound(
                f"no adapter for capability={capability!r} name={name!r}; "
                f"available={list(self._adapters.get(capability, {}))}"
            ) from exc
        return factory(**kwargs)

    # -- services (domain-neutral platform capabilities) --
    def register_service(self, capability: str, name: str, factory: Factory) -> None:
        if capability not in SERVICE_PROTOCOLS:
            raise ProtocolViolation(f"unknown service capability {capability!r}")
        self._services.setdefault(capability, {})[name] = factory
        log.debug("registered_service", capability=capability, name=name)

    def service(self, capability: str, name: str, **kwargs: Any) -> Any:
        try:
            factory = self._services[capability][name]
        except KeyError as exc:
            raise ProviderNotFound(
                f"no service for capability={capability!r} name={name!r}; "
                f"available={list(self._services.get(capability, {}))}"
            ) from exc
        instance = factory(**kwargs)
        proto = SERVICE_PROTOCOLS[capability]
        if not isinstance(instance, proto):  # runtime_checkable protocols
            raise ProtocolViolation(
                f"service {name!r} does not satisfy {proto.__name__} for {capability!r}"
            )
        return instance

    # -- domain packs --
    def register_domain_pack(self, pack_id: str, factory: Factory) -> None:
        self._domain_packs[pack_id] = factory
        log.debug("registered_domain_pack", id=pack_id)

    def domain_pack(self, pack_id: str, **kwargs: Any) -> Any:
        try:
            return self._domain_packs[pack_id](**kwargs)
        except KeyError as exc:
            raise ProviderNotFound(f"domain-pack {pack_id!r} not registered") from exc

    # -- introspection (powers the console + `aegoria doctor`) --
    def describe(self) -> dict[str, Any]:
        return {
            "adapters": {cap: sorted(names) for cap, names in self._adapters.items()},
            "services": {cap: sorted(names) for cap, names in self._services.items()},
            "domain_packs": sorted(self._domain_packs),
        }


# Global default registry + decorator sugar so providers self-register on import.
registry = Registry()


def adapter(capability: str, name: str) -> Callable[[Factory], Factory]:
    def deco(factory: Factory) -> Factory:
        registry.register_adapter(capability, name, factory)
        return factory
    return deco


def service(capability: str, name: str) -> Callable[[Factory], Factory]:
    def deco(factory: Factory) -> Factory:
        registry.register_service(capability, name, factory)
        return factory
    return deco


def domain_pack(pack_id: str) -> Callable[[Factory], Factory]:
    def deco(factory: Factory) -> Factory:
        registry.register_domain_pack(pack_id, factory)
        return factory
    return deco


def load_entrypoints(group: str = "aegoria.providers") -> int:
    """Discover providers shipped by installed packages via Python entry points.

    This is how adapters and domain-packs plug in without the core importing them:
    each package advertises an ``aegoria.providers`` entry point whose import
    triggers its ``@adapter`` / ``@service`` / ``@domain_pack`` registrations.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return 0
    count = 0
    eps = entry_points()
    selected = eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])  # type: ignore[attr-defined]
    for ep in selected:
        try:
            ep.load()
            count += 1
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("entrypoint_load_failed", entrypoint=ep.name, error=str(exc))
    return count
