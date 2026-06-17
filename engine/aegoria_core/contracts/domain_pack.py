"""Domain-pack contract — how a brand-new market onboards *declaratively*.

A domain-pack is a portable, versioned plugin. It carries everything Aegoria
needs to treat a new market as a first-class participant — schemas, ontology,
quality rules, ML model references, ingestion connectors, and default access
policy — as **data**. The core engine loads it; the core engine never changes.

Most of a pack is the declarative ``DomainPackManifest`` (YAML/JSON). Optional
Python hooks let a pack ship custom connectors, quality checks or model loaders,
but those hooks bind to the same adapter/service protocols as everything else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, Field

from .models import (
    License,
    Jurisdiction,
    Modality,
    QualityRule,
    TableSchema,
)


class OntologyTerm(BaseModel):
    """A concept in the domain vocabulary, optionally aligned to an external standard."""

    id: str  # local term id, e.g. "emissions:Facility"
    label: str
    parent: Optional[str] = None
    same_as: list[str] = Field(default_factory=list)  # external URIs (FIBO, QUDT, schema.org)
    description: str = ""


class SemanticMapping(BaseModel):
    """Maps a dataset field to an ontology term — how raw columns gain meaning + interoperate."""

    dataset: str
    field: str
    term: str  # OntologyTerm.id


class ConnectorSpec(BaseModel):
    """Declares an ingestion source the pack knows how to read."""

    id: str
    modality: Modality = Modality.STRUCTURED
    adapter: str = "file"  # which ingestion connector adapter to use
    format: str = "csv"  # csv | parquet | json | geojson | image | kafka | api ...
    options: dict[str, Any] = Field(default_factory=dict)
    target_dataset: str = ""
    schedule: Optional[str] = None  # cron-ish, for orchestration


class ModelSpec(BaseModel):
    """Reference to a per-domain ML model (anomaly/predict/verify). The core stays generic."""

    id: str
    task: str  # anomaly | forecast | classify | verify_content | embed
    runtime: str = "sklearn"  # sklearn | onnx | torch | remote
    uri: Optional[str] = None  # model artifact location
    target_dataset: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)


class AccessPolicySpec(BaseModel):
    """Default ABAC/RBAC policy the pack ships. Sovereignty + privacy as defaults."""

    id: str
    description: str = ""
    effect: str = "allow"  # allow | deny
    roles: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)  # glob over pack datasets
    # ABAC condition expression over principal/resource attributes (CEL-like).
    condition: Optional[str] = None
    obligations: list[dict[str, Any]] = Field(default_factory=list)  # e.g. {kind: differential_privacy, params: {...}}


class DatasetSpec(BaseModel):
    """A dataset the pack defines, with its schema and governance defaults."""

    name: str
    title: str = ""
    description: str = ""
    modality: Modality = Modality.STRUCTURED
    schema_: TableSchema = Field(alias="schema")
    license: License = Field(default_factory=License)
    jurisdiction: Jurisdiction = Field(default_factory=Jurisdiction)
    quality_rules: list[QualityRule] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    sample_data: Optional[str] = None  # path/glob to sample data shipped with the pack

    model_config = {"populate_by_name": True}


class DomainPackManifest(BaseModel):
    """The complete declarative description of a market. This file IS the onboarding."""

    api_version: str = "aegoria.dev/v1"
    kind: str = "DomainPack"
    id: str  # e.g. "climate-emissions"
    name: str
    version: str = "0.1.0"
    description: str = ""
    maintainer: str = ""
    license: License = Field(default_factory=License)
    # Core compatibility range this pack was authored against (semver).
    core_compat: str = ">=0.1.0,<1.0.0"
    modalities: list[Modality] = Field(default_factory=list)
    datasets: list[DatasetSpec] = Field(default_factory=list)
    ontology: list[OntologyTerm] = Field(default_factory=list)
    semantic_mappings: list[SemanticMapping] = Field(default_factory=list)
    connectors: list[ConnectorSpec] = Field(default_factory=list)
    models: list[ModelSpec] = Field(default_factory=list)
    access_policies: list[AccessPolicySpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DomainPackManifest":
        data = yaml.safe_load(Path(path).read_text())
        return cls.model_validate(data)

    def dataset(self, name: str) -> Optional[DatasetSpec]:
        return next((d for d in self.datasets if d.name == name), None)


@runtime_checkable
class DomainPack(Protocol):
    """Runtime view of a loaded pack. The manifest is the contract; hooks are optional."""

    @property
    def manifest(self) -> DomainPackManifest: ...

    # Optional code hooks (a pure-declarative pack returns None / no-ops):
    def connectors(self) -> dict[str, Any]:  # id -> callable producing pa.Table batches
        ...
    def models(self) -> dict[str, Any]:  # id -> loaded model object
        ...
    def custom_quality(self) -> dict[str, Any]:  # rule_id -> callable(table)->RuleResult
        ...
