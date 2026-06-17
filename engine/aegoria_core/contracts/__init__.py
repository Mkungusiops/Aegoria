"""Aegoria stable contracts: models, adapter protocols, service protocols, domain-pack."""

from .adapters import (
    CarbonSource,
    CatalogAdapter,
    ComputeAdapter,
    IdentityAdapter,
    ProvenanceSigner,
    StorageAdapter,
    StreamAdapter,
)
from .domain_pack import (
    AccessPolicySpec,
    ConnectorSpec,
    DatasetSpec,
    DomainPack,
    DomainPackManifest,
    ModelSpec,
    OntologyTerm,
    SemanticMapping,
)
from .models import (
    AccessDecision,
    AccessRequest,
    Action,
    CarbonReading,
    DatasetMetadata,
    DatasetRef,
    Entity,
    FairFlags,
    FieldSchema,
    FieldType,
    Jurisdiction,
    License,
    LineageEdge,
    Modality,
    Obligation,
    Principal,
    PrivacyBudget,
    ProvenanceRecord,
    QualityReport,
    QualityRule,
    QueryResult,
    QuerySpec,
    QueryStats,
    Relation,
    RuleResult,
    Sensitivity,
    TableSchema,
)
from .services import (
    SERVICE_PROTOCOLS,
    CatalogService,
    ComputeScheduler,
    GovernanceService,
    IngestionService,
    KnowledgeGraphService,
    LakehouseService,
    MLService,
    ProvenanceService,
)

__all__ = [
    # models
    "AccessDecision", "AccessRequest", "Action", "CarbonReading", "DatasetMetadata",
    "DatasetRef", "Entity", "FairFlags", "FieldSchema", "FieldType", "Jurisdiction",
    "License", "LineageEdge", "Modality", "Obligation", "Principal", "PrivacyBudget",
    "ProvenanceRecord", "QualityReport", "QualityRule", "QueryResult", "QuerySpec",
    "QueryStats", "Relation", "RuleResult", "Sensitivity", "TableSchema",
    # adapters
    "CarbonSource", "CatalogAdapter", "ComputeAdapter", "IdentityAdapter",
    "ProvenanceSigner", "StorageAdapter", "StreamAdapter",
    # services
    "SERVICE_PROTOCOLS", "CatalogService", "ComputeScheduler", "GovernanceService",
    "IngestionService", "KnowledgeGraphService", "LakehouseService", "MLService",
    "ProvenanceService",
    # domain pack
    "AccessPolicySpec", "ConnectorSpec", "DatasetSpec", "DomainPack",
    "DomainPackManifest", "ModelSpec", "OntologyTerm", "SemanticMapping",
]
