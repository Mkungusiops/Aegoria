"""Contract sanity — every wired provider satisfies its declared protocol.

After ``AegoriaEngine.bootstrap``:

* every service named in ``SERVICE_PROTOCOLS`` resolves and is an instance of its
  ``runtime_checkable`` protocol (the registry enforces this on resolution, but we
  assert it explicitly here against the engine's public service accessors), and
* every adapter the default config selects resolves and satisfies its adapter
  protocol from ``aegoria_core.contracts.adapters``.

This is the guard that keeps providers swappable: the engine binds to protocols,
so anything passing here is a drop-in replacement.
"""

from __future__ import annotations

import pytest

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts import adapters as adapter_contracts
from aegoria_core.contracts.services import SERVICE_PROTOCOLS

# capability -> adapter protocol the configured adapter must satisfy.
ADAPTER_PROTOCOLS = {
    "storage": adapter_contracts.StorageAdapter,
    "catalog": adapter_contracts.CatalogAdapter,
    "compute": adapter_contracts.ComputeAdapter,
    "stream": adapter_contracts.StreamAdapter,
    "identity": adapter_contracts.IdentityAdapter,
    "provenance": adapter_contracts.ProvenanceSigner,
    "carbon": adapter_contracts.CarbonSource,
}


@pytest.fixture()
def engine(tmp_path) -> AegoriaEngine:
    config = AegoriaConfig(
        warehouse_uri=str(tmp_path / "warehouse"),
        catalog_uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        domain_pack_paths=[],
    )
    return AegoriaEngine.bootstrap(config)


@pytest.mark.parametrize("capability", sorted(SERVICE_PROTOCOLS))
def test_every_default_service_satisfies_its_protocol(engine: AegoriaEngine, capability: str) -> None:
    protocol = SERVICE_PROTOCOLS[capability]
    service = engine.ctx.service(capability)
    assert isinstance(service, protocol), (
        f"service {capability!r} ({type(service).__name__}) does not satisfy {protocol.__name__}"
    )


@pytest.mark.parametrize("capability", sorted(ADAPTER_PROTOCOLS))
def test_every_configured_adapter_resolves_and_satisfies_protocol(
    engine: AegoriaEngine, capability: str
) -> None:
    assert capability in engine.config.adapters, f"{capability} not selected by config"
    adapter = engine.ctx.adapter(capability)
    protocol = ADAPTER_PROTOCOLS[capability]
    assert isinstance(adapter, protocol), (
        f"adapter {capability!r} ({type(adapter).__name__}) does not satisfy {protocol.__name__}"
    )
    # Every adapter advertises its provider name (used by health/registry describe).
    assert getattr(adapter, "name", None), f"adapter {capability!r} missing a name"


def test_service_accessors_match_service_protocols(engine: AegoriaEngine) -> None:
    """The engine's public service properties resolve the same protocol set."""
    accessors = {
        "lakehouse": engine.lakehouse,
        "ingestion": engine.ingestion,
        "catalog": engine.catalog,
        "governance": engine.governance,
        "scheduler": engine.scheduler,
        "knowledge_graph": engine.knowledge_graph,
        "ml": engine.ml,
        "provenance": engine.provenance,
    }
    assert set(accessors) == set(SERVICE_PROTOCOLS)
    for capability, service in accessors.items():
        assert isinstance(service, SERVICE_PROTOCOLS[capability])


def test_health_reports_all_configured_providers(engine: AegoriaEngine) -> None:
    providers = engine.health()["providers"]
    assert set(ADAPTER_PROTOCOLS) <= set(providers["adapters"])
    assert set(SERVICE_PROTOCOLS) <= set(providers["services"])
