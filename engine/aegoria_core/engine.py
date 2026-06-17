"""AegoriaEngine — the domain-neutral orchestrator.

This is the part the constraints call "the core engine that never changes." It
imports **no** concrete adapter, service or domain-pack. It only:

  1. reads declarative ``AegoriaConfig``,
  2. resolves providers from the ``Registry`` by capability + name, and
  3. wires them into end-to-end flows (ingest, govern, schedule, query).

Adding a market is ``load_domain_pack(manifest)`` + data. Adding a cloud/format
is registering a new adapter. Neither edits this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .config import AegoriaConfig
from .contracts.domain_pack import DomainPackManifest
from .contracts.models import (
    AccessRequest,
    Action,
    CarbonReading,
    DatasetMetadata,
    DatasetRef,
    LineageEdge,
    Obligation,
    Principal,
    QueryResult,
    QuerySpec,
)
from .errors import AccessDenied, DomainPackError
from .registry import Registry, load_entrypoints, registry as global_registry

log = structlog.get_logger("aegoria.engine")

CORE_VERSION = "0.1.0"


@dataclass
class EngineContext:
    """Shared context handed to every provider factory. Lazily resolves + caches
    adapters and services so providers can depend on each other without ordering."""

    config: AegoriaConfig
    registry: Registry
    _adapters: dict[str, Any] = field(default_factory=dict)
    _services: dict[str, Any] = field(default_factory=dict)

    def adapter(self, capability: str) -> Any:
        if capability not in self._adapters:
            sel = self.config.adapters[capability]
            self._adapters[capability] = self.registry.adapter(
                capability, sel.name, config=self.config, ctx=self, **sel.options
            )
        return self._adapters[capability]

    def service(self, capability: str) -> Any:
        if capability not in self._services:
            name = self.config.services[capability]
            self._services[capability] = self.registry.service(capability, name, ctx=self)
        return self._services[capability]


class AegoriaEngine:
    """The single entry point downstream code (CLI, API, notebooks) talks to."""

    def __init__(self, config: AegoriaConfig, registry: Optional[Registry] = None) -> None:
        self.config = config
        self.registry = registry or global_registry
        self.ctx = EngineContext(config=config, registry=self.registry)
        self._loaded_packs: dict[str, DomainPackManifest] = {}

    # ------------------------------------------------------------------ #
    @classmethod
    def bootstrap(cls, config: Optional[AegoriaConfig] = None, *, discover: bool = True) -> "AegoriaEngine":
        """Create an engine: discover providers, build context, load configured packs."""
        cfg = config or AegoriaConfig.load()
        if discover:
            n = load_entrypoints()
            log.info("providers_discovered", count=n)
        engine = cls(cfg)
        engine.load_domain_packs()
        return engine

    # -- service accessors (resolved lazily; never concrete imports) ---- #
    @property
    def lakehouse(self) -> Any: return self.ctx.service("lakehouse")
    @property
    def ingestion(self) -> Any: return self.ctx.service("ingestion")
    @property
    def catalog(self) -> Any: return self.ctx.service("catalog")
    @property
    def governance(self) -> Any: return self.ctx.service("governance")
    @property
    def scheduler(self) -> Any: return self.ctx.service("scheduler")
    @property
    def knowledge_graph(self) -> Any: return self.ctx.service("knowledge_graph")
    @property
    def ml(self) -> Any: return self.ctx.service("ml")
    @property
    def provenance(self) -> Any: return self.ctx.service("provenance")

    # ------------------------------------------------------------------ #
    # Domain-pack onboarding — declarative, core untouched.
    # ------------------------------------------------------------------ #
    def load_domain_packs(self) -> list[str]:
        """Discover + load packs from configured paths and registered entry points."""
        from pathlib import Path

        loaded: list[str] = []
        for base in self.config.domain_pack_paths:
            root = Path(base)
            if not root.exists():
                continue
            for manifest_path in sorted(root.glob("*/manifest.yaml")):
                manifest = DomainPackManifest.from_yaml(manifest_path)
                if self.config.domain_packs and manifest.id not in self.config.domain_packs:
                    continue
                self.load_domain_pack(manifest)
                loaded.append(manifest.id)
        return loaded

    def load_domain_pack(self, manifest: DomainPackManifest) -> None:
        """Register a market's schemas, policies, ontology and models into the platform.

        Pure orchestration over service protocols — domain meaning stays in the
        manifest, not in this method."""
        self._check_compat(manifest)
        catalog = self.catalog
        for ds in manifest.datasets:
            meta = DatasetMetadata(
                ref=DatasetRef(domain=manifest.id, name=ds.name, version=manifest.version),
                title=ds.title or ds.name,
                description=ds.description,
                schema=ds.schema_,
                modality=ds.modality,
                owner=manifest.maintainer,
                tags=ds.tags,
                license=ds.license,
                jurisdiction=ds.jurisdiction,
            )
            catalog.register(meta)
        # Access policies -> governance (best-effort: governance may ingest them).
        gov = self.governance
        if hasattr(gov, "load_policies"):
            gov.load_policies(manifest.id, manifest.access_policies)
        # ML models -> ml service.
        ml = self.ml
        for m in manifest.models:
            ml.register_model(manifest.id, m.id, m.model_dump())
        # Ontology -> knowledge graph.
        kg = self.knowledge_graph
        if hasattr(kg, "load_ontology"):
            kg.load_ontology(manifest.id, manifest.ontology, manifest.semantic_mappings)
        self._loaded_packs[manifest.id] = manifest
        log.info("domain_pack_loaded", id=manifest.id, datasets=len(manifest.datasets))

    def _check_compat(self, manifest: DomainPackManifest) -> None:
        try:
            if Version(CORE_VERSION) not in SpecifierSet(manifest.core_compat):
                raise DomainPackError(
                    f"pack {manifest.id!r} requires core {manifest.core_compat}, have {CORE_VERSION}"
                )
        except DomainPackError:
            raise
        except Exception as exc:  # malformed specifier
            raise DomainPackError(f"pack {manifest.id!r} has invalid core_compat: {exc}") from exc

    @property
    def domain_packs(self) -> dict[str, DomainPackManifest]:
        return dict(self._loaded_packs)

    # ------------------------------------------------------------------ #
    # End-to-end flows.
    # ------------------------------------------------------------------ #
    def ingest(self, *, domain: str, connector: str, source_uri: str, dataset: str,
               principal: Optional[str] = None, options: Optional[dict[str, Any]] = None) -> DatasetMetadata:
        """Ingest a source into the lakehouse with provenance attached at capture."""
        manifest = self._loaded_packs.get(domain)
        if manifest is None:
            raise DomainPackError(f"domain {domain!r} is not loaded")
        ds = manifest.dataset(dataset)
        if ds is None:
            raise DomainPackError(f"dataset {dataset!r} not declared by domain {domain!r}")
        meta = self.ingestion.ingest(
            domain=domain, connector=connector, source_uri=source_uri,
            schema=ds.schema_, options=options or {}, principal=principal,
        )
        self.catalog.record_lineage(
            LineageEdge(src=DatasetRef(domain=domain, name=f"source:{connector}", version="ext"),
                        dst=meta.ref, operation="ingest")
        )
        return meta

    def query(self, spec: QuerySpec, principal: Optional[Principal] = None) -> QueryResult:
        """Authorize -> carbon-aware placement -> execute -> enforce obligations."""
        principal = principal or Principal(subject="anonymous", roles=["public"])
        obligations: list[Obligation] = []
        for ds in spec.datasets:
            meta = self.catalog.get(ds)
            if meta is None:
                raise AccessDenied(f"unknown dataset {ds.id}")
            decision = self.governance.authorize(
                AccessRequest(principal=principal, dataset=ds, action=Action.QUERY, purpose=spec.purpose),
                meta,
            )
            if not decision.allow:
                raise AccessDenied(f"{ds.id}: {decision.reason}")
            obligations.extend(decision.obligations)
        table_paths = {ds.name: self.lakehouse.table_location(ds) for ds in spec.datasets}
        result = self.scheduler.execute(spec, table_paths, obligations=obligations)
        return result

    def carbon_snapshot(self) -> list[CarbonReading]:
        return self.scheduler.carbon_snapshot()

    # ------------------------------------------------------------------ #
    def health(self) -> dict[str, Any]:
        return {
            "core_version": CORE_VERSION,
            "deployment": self.config.deployment,
            "providers": self.registry.describe(),
            "domain_packs": [
                {"id": m.id, "name": m.name, "version": m.version, "datasets": len(m.datasets)}
                for m in self._loaded_packs.values()
            ],
            "privacy": self.config.privacy.model_dump(),
        }
