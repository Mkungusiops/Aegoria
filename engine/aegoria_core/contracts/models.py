"""Aegoria core vocabulary — the stable, domain-neutral data model.

Every concept here is deliberately market-agnostic: a `Dataset` of satellite
imagery, of credit applications, of ICU vitals, or of freight telemetry is the
*same* kind of object to the core. Domain meaning is attached via ``semantic_type``
links into a domain-pack's ontology, never hard-coded here.

These models are part of the frozen core: adapters, services, and domain-packs
all speak this vocabulary. Changing it is a core-version event; adding a domain
must never require touching it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Modalities & classification
# --------------------------------------------------------------------------- #
class Modality(str, Enum):
    """The shape of the data, independent of what it means."""

    STRUCTURED = "structured"
    TIME_SERIES = "time_series"
    GEOSPATIAL = "geospatial"
    IMAGERY = "imagery"
    SENSOR_STREAM = "sensor_stream"
    EVENT_STREAM = "event_stream"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    GRAPH = "graph"


class Sensitivity(str, Enum):
    """How carefully a field/dataset must be handled. Drives default policy."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"
    PHI = "phi"  # protected health information
    FINANCIAL = "financial"
    RESTRICTED = "restricted"


class FieldType(str, Enum):
    STRING = "string"
    INT = "int"
    LONG = "long"
    FLOAT = "float"
    DOUBLE = "double"
    BOOL = "bool"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BINARY = "binary"
    GEOMETRY = "geometry"  # WKB/WKT geometry
    JSON = "json"
    ARRAY = "array"
    STRUCT = "struct"


# --------------------------------------------------------------------------- #
# Schemas (schema-on-read; declared by domain-packs, never by the core)
# --------------------------------------------------------------------------- #
class FieldSchema(BaseModel):
    name: str
    type: FieldType
    nullable: bool = True
    description: str = ""
    unit: Optional[str] = None
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    # Link to a term in the domain-pack ontology / external vocab (e.g. a QUDT,
    # FIBO, or schema.org URI). This is how meaning enters the system.
    semantic_type: Optional[str] = None
    pii: bool = False
    children: list["FieldSchema"] = Field(default_factory=list)  # struct/array


class TableSchema(BaseModel):
    name: str
    version: str = "1.0.0"
    modality: Modality = Modality.STRUCTURED
    fields: list[FieldSchema] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)
    partition_by: list[str] = Field(default_factory=list)
    description: str = ""

    def field(self, name: str) -> Optional[FieldSchema]:
        return next((f for f in self.fields if f.name == name), None)

    @property
    def pii_fields(self) -> list[str]:
        return [f.name for f in self.fields if f.pii or f.sensitivity in (Sensitivity.PII, Sensitivity.PHI)]


FieldSchema.model_rebuild()


# --------------------------------------------------------------------------- #
# Licensing, jurisdiction, provenance, lineage
# --------------------------------------------------------------------------- #
class License(BaseModel):
    spdx_id: str = "CC-BY-4.0"
    name: str = "Creative Commons Attribution 4.0"
    url: Optional[str] = None
    attribution: Optional[str] = None
    redistributable: bool = True
    commercial_use: bool = True
    notes: str = ""


class Jurisdiction(BaseModel):
    """Where the data legally lives. Drives sovereignty + which regs apply."""

    code: str = "GLOBAL"  # ISO-3166 alpha-2, region code, or GLOBAL
    region: str = "global"
    regulations: list[str] = Field(default_factory=list)  # GDPR, HIPAA, CCPA, ...
    residency_required: bool = False  # data may not leave `code`


class ProvenanceRecord(BaseModel):
    """Machine-readable provenance attached at the moment of capture."""

    source_uri: str
    captured_at: datetime = Field(default_factory=_utcnow)
    captured_by: str = "unknown"  # principal / connector id
    method: str = "ingest"  # ingest | derive | join | model | manual
    checksum_sha256: Optional[str] = None
    # Cryptographic content signature (e.g. C2PA manifest digest).
    content_signature: Optional[str] = None
    signature_alg: Optional[str] = None
    software_agent: str = "aegoria-core"
    software_version: str = "0.1.0"
    upstream: list["DatasetRef"] = Field(default_factory=list)
    transformation: Optional[str] = None  # human/machine description of the op
    extra: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    src: "DatasetRef"
    dst: "DatasetRef"
    operation: str  # ingest | transform | join | aggregate | model | publish
    run_id: Optional[str] = None
    at: datetime = Field(default_factory=_utcnow)
    code_ref: Optional[str] = None  # git sha / pipeline node id


# --------------------------------------------------------------------------- #
# Datasets & FAIR metadata
# --------------------------------------------------------------------------- #
class DatasetRef(BaseModel):
    """A stable, domain-qualified pointer to a dataset version."""

    domain: str  # which domain-pack owns it, e.g. "climate-emissions"
    name: str
    version: str = "1.0.0"

    @property
    def id(self) -> str:
        return f"{self.domain}/{self.name}@{self.version}"

    def __str__(self) -> str:  # noqa: D401
        return self.id

    def __hash__(self) -> int:
        return hash(self.id)


class FairFlags(BaseModel):
    """FAIR self-assessment (Findable, Accessible, Interoperable, Reusable)."""

    findable: bool = False        # has persistent id + rich metadata + indexed
    accessible: bool = False      # retrievable via open protocol + auth
    interoperable: bool = False   # uses shared vocab / semantic_type mappings
    reusable: bool = False        # clear license + provenance + quality

    @property
    def score(self) -> float:
        return sum([self.findable, self.accessible, self.interoperable, self.reusable]) / 4.0


class DatasetMetadata(BaseModel):
    """The FAIR catalog record — everything needed to find, trust and reuse data."""

    ref: DatasetRef
    title: str = ""
    description: str = ""
    schema_: TableSchema = Field(alias="schema")
    modality: Modality = Modality.STRUCTURED
    owner: str = "unknown"
    tags: list[str] = Field(default_factory=list)
    license: License = Field(default_factory=License)
    jurisdiction: Jurisdiction = Field(default_factory=Jurisdiction)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    fair: FairFlags = Field(default_factory=FairFlags)
    semantic_uri: Optional[str] = None
    quality_score: float = 0.0  # 0..1, last QualityReport.score
    row_count: int = 0
    byte_size: int = 0
    location_uri: Optional[str] = None  # physical table location
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# --------------------------------------------------------------------------- #
# Identity, access, privacy
# --------------------------------------------------------------------------- #
class Principal(BaseModel):
    subject: str
    display_name: str = ""
    roles: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)  # ABAC attributes
    jurisdiction: str = "GLOBAL"
    clearance: Sensitivity = Sensitivity.INTERNAL


class Action(str, Enum):
    READ = "read"
    QUERY = "query"
    SAMPLE = "sample"
    AGGREGATE = "aggregate"
    EXPORT = "export"
    TRAIN = "train"
    WRITE = "write"
    ADMIN = "admin"


class AccessRequest(BaseModel):
    principal: Principal
    dataset: DatasetRef
    action: Action
    purpose: str = ""
    fields: list[str] = Field(default_factory=list)


class Obligation(BaseModel):
    """A condition the platform must enforce when access is granted."""

    kind: str  # mask | tokenize | differential_privacy | aggregate_only | row_filter | watermark | residency
    params: dict[str, Any] = Field(default_factory=dict)


class AccessDecision(BaseModel):
    allow: bool
    reason: str = ""
    obligations: list[Obligation] = Field(default_factory=list)
    policy_id: Optional[str] = None


class PrivacyBudget(BaseModel):
    """Differential-privacy accounting per (principal, dataset)."""

    epsilon: float = 1.0
    delta: float = 1e-6
    spent: float = 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, self.epsilon - self.spent)


# --------------------------------------------------------------------------- #
# Quality
# --------------------------------------------------------------------------- #
class QualityRule(BaseModel):
    """Declared by a domain-pack; evaluated by the core, never authored by it."""

    id: str
    field: Optional[str] = None
    kind: str  # not_null | unique | range | regex | enum | freshness | referential | custom
    params: dict[str, Any] = Field(default_factory=dict)
    severity: str = "error"  # error | warn | info
    description: str = ""


class RuleResult(BaseModel):
    rule_id: str
    passed: bool
    violations: int = 0
    sampled: int = 0
    message: str = ""


class QualityReport(BaseModel):
    dataset: DatasetRef
    evaluated_at: datetime = Field(default_factory=_utcnow)
    results: list[RuleResult] = Field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results if True)


# --------------------------------------------------------------------------- #
# Compute, carbon, query
# --------------------------------------------------------------------------- #
class CarbonReading(BaseModel):
    """Grid carbon intensity used by the carbon-aware scheduler."""

    region: str
    gco2_per_kwh: float
    renewable_fraction: float = 0.0
    source: str = "static"  # static | electricitymaps | watttime | simulated
    at: datetime = Field(default_factory=_utcnow)


class QuerySpec(BaseModel):
    sql: Optional[str] = None
    datasets: list[DatasetRef] = Field(default_factory=list)
    purpose: str = ""
    epsilon: Optional[float] = None  # request differential privacy if set
    limit: Optional[int] = None
    preferred_engine: Optional[str] = None  # adapter hint, scheduler may override


class QueryStats(BaseModel):
    rows: int = 0
    bytes_scanned: int = 0
    duration_ms: float = 0.0
    engine: str = "duckdb"
    region: str = "local"
    energy_kwh: float = 0.0
    carbon_g: float = 0.0
    dp_applied: bool = False
    epsilon_spent: float = 0.0


class QueryResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    stats: QueryStats = Field(default_factory=QueryStats)


# --------------------------------------------------------------------------- #
# Knowledge graph
# --------------------------------------------------------------------------- #
class Entity(BaseModel):
    id: str
    type: str  # ontology class, e.g. "Facility", "Borrower", "Region"
    domain: str
    properties: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    src: str
    dst: str
    type: str  # predicate, e.g. "located_in", "owns", "emits"
    confidence: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


# Resolve forward references.
ProvenanceRecord.model_rebuild()
LineageEdge.model_rebuild()
