# Glossary

Canonical definitions for the vocabulary used across Aegoria. Defined once here;
referenced everywhere.

### Adapter
A provider-agnostic implementation of an *infrastructure* protocol (storage, catalog,
compute, stream, identity, provenance, carbon). Swapping an adapter changes the backend
without touching the engine. See [Adapter & Service Interfaces](./reference/adapter-interfaces.md).

### ABAC (Attribute-Based Access Control)
Authorization driven by *attributes* (jurisdiction, purpose, owner, clearance) evaluated as
`condition` expressions on a policy. Layered on top of RBAC. See [Access Control & RBAC](./reference/access-control-rbac.md).

### ADR (Architecture Decision Record)
An immutable record of a significant architectural decision, its context, and consequences.
See [decisions/](./architecture/decisions/).

### Carbon-aware scheduling
Placing a compute job on the *greenest capable* region/engine using live grid carbon
intensity, to minimize gCO₂ per query. Implemented by the `ComputeScheduler`.

### Catalog (FAIR)
The searchable registry of datasets and their metadata (Findable, Accessible, Interoperable,
Reusable), plus the lineage graph. Backed by `CatalogService`.

### C2PA / Content provenance
A cryptographic, machine-readable record of where data came from and that it hasn't been
tampered with, attached at the moment of capture. (Aegoria's lite build uses an HMAC stand-in
behind the `ProvenanceSigner` protocol.)

### Core engine
The frozen orchestrator (`engine.py`) + contracts + registry + config that **never changes**
when a market or backend is added. See [ADR 0001](./architecture/decisions/0001-core-engine-never-changes.md).

### Differential privacy (DP)
A formal privacy guarantee: calibrated noise is added to query results so individuals can't be
re-identified, tracked by an (ε, δ) **budget**. Smaller ε = stronger privacy.

### Domain-pack
A portable, versioned, **declarative** plugin that onboards a market: schemas, ontology,
quality rules, ML-model references, and access policy — as data, not code. See the
[Domain-Pack Specification](./reference/domain-pack-spec.md).

### Federated learning
Training a shared model across data that stays in place; only model updates (not raw data)
cross organizational/jurisdictional boundaries.

### Lakehouse
An open-table-format (Apache Iceberg) data layer over object storage that combines a data
lake's openness with a warehouse's ACID/schema guarantees. **Schema-on-read.** See
[ADR 0002](./architecture/decisions/0002-iceberg-lakehouse-and-open-formats.md).

### Lineage
The graph of how a dataset was derived from its upstreams (ingest → transform → model →
publish), recorded as edges in the catalog.

### Modality
The *shape* of data independent of its meaning: structured, time-series, geospatial, imagery,
sensor-stream, event-stream, text, audio, video, graph.

### Obligation
A condition the platform must enforce when access is granted: `mask`, `aggregate_only`,
`differential_privacy`, `residency`, `watermark`.

### Ontology
The domain vocabulary (terms + relationships), optionally aligned to external standards
(FIBO, QUDT, schema.org), that gives raw columns meaning and enables cross-source interoperability.

### Principal
The authenticated identity making a request: `subject`, `roles[]`, `attributes{}`,
`jurisdiction`, `clearance`. Produced by an `IdentityAdapter`.

### Provider
Any registered implementation — an adapter, a service, or a domain-pack — resolved by the
registry by capability + name.

### RBAC (Role-Based Access Control)
Authorization driven by *roles* on the principal matched against policy role-lists and
built-in role rules. The apex role is **super-admin** (break-glass). See
[Access Control & RBAC](./reference/access-control-rbac.md).

### Registry
The indirection that lets the engine resolve providers by capability + name without importing
concrete implementations — the mechanical guarantee behind [ADR 0001](./architecture/decisions/0001-core-engine-never-changes.md).

### Residency / sovereignty
The requirement that data bound to a jurisdiction is processed only within it. Enforced before
compute placement.

### Schema-on-read
Applying a schema when data is *read*, not when written — so each domain defines its own
schemas without reshaping the storage layer.

### Service
A domain-neutral *capability* of the core (lakehouse, ingestion, catalog, governance,
scheduler, knowledge-graph, ML, provenance), resolved by protocol and swappable.

### Super-admin
The apex RBAC role (`superadmin`/`root`): unrestricted, break-glass access with no obligations.
See [Access Control & RBAC](./reference/access-control-rbac.md).

### Trust fabric
The collective privacy + governance layer: PII classification, RBAC/ABAC, differential privacy,
federated learning, and content provenance.

→ Back to [Documentation home](./README.md)
