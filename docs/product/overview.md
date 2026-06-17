# Aegoria — Overview

> **One planet. Every domain. Data you can trust.**

Aegoria is an open-source, **planet-scale, market-agnostic, privacy-preserving big-data
lakehouse platform**. It lets any organisation — a climate-monitoring NGO, a consumer
lender, a hospital network, a port authority — onboard onto the *same* trustworthy data
infrastructure without that infrastructure being rebuilt, re-licensed, or compromised for
their particular market.

This document is the front door. It explains what Aegoria is, the problems it attacks, the
constraints it refuses to break, and where to read next.

---

## 1. What Aegoria is

Aegoria is **one core engine** surrounded by **swappable adapters** and fed by
**declarative domain-packs**.

- **The core engine** (`aegoria_core`) is domain-neutral and infra-neutral. It reads a
  declarative config, resolves providers from a registry by *capability + name*, and wires
  them into end-to-end flows: ingest → govern → place → execute → enforce. It imports no
  concrete cloud, no concrete format, and no concrete market. See `engine/aegoria_core/engine.py`.

- **Adapters** are protocols (`StorageAdapter`, `CatalogAdapter`, `ComputeAdapter`,
  `StreamAdapter`, `IdentityAdapter`, `ProvenanceSigner`, `CarbonSource`). Each infra
  backend — local disk or S3, DuckDB or Spark, an inproc bus or Kafka — is a provider
  registered under a capability. Swap the provider, keep the engine. See
  `engine/aegoria_core/contracts/adapters.py`.

- **Services** are the higher-order protocols the engine orchestrates (`LakehouseService`,
  `IngestionService`, `CatalogService`, `GovernanceService`, `ComputeScheduler`,
  `KnowledgeGraphService`, `MLService`, `ProvenanceService`). See
  `engine/aegoria_core/contracts/services.py`.

- **Domain-packs** are portable, versioned plugins that describe an entire market *as data*:
  schemas, ontology, semantic mappings, quality rules, ingestion connectors, ML model
  references, and default access policy. **Loading a pack is the whole act of onboarding a
  market.** See `engine/aegoria_core/contracts/domain_pack.py` and the two shipped
  reference packs in `domain-packs/`.

Two deliberately **unrelated** reference domains ship with the platform and prove it is
genuinely market-agnostic:

| Pack | Market | Modalities exercised | What it proves |
|------|--------|----------------------|----------------|
| `climate-emissions` | Environmental monitoring | time-series, geospatial, imagery, sensor-stream | Open data, multi-modal ingest, content watermarking, carbon-aware compute |
| `consumer-credit` | Retail lending | structured, time-series | PII handling, GDPR residency/sovereignty, differential privacy, fairness-aware ML |

If a decision works for *both* of these — satellite methane plumes and EU loan
applications have nothing in common — it is a decision that generalises to any market.

---

## 2. The problems Aegoria attacks

Aegoria exists because the data economy is failing on five fronts at once. Each problem is
attacked by a specific, verifiable platform capability — not a slogan.

### 2.1 Fragmentation and silos
Every sector reinvents its own warehouse, its own catalog, its own governance, its own
sharing protocol. The result is duplicated cost, incompatible vocabularies, and data that
cannot cross an organisational or sectoral boundary even when sharing would be lawful and
beneficial.
**Aegoria's answer:** one core engine plus declarative domain-packs. New markets onboard
without forking the platform, and an open ontology layer (`OntologyTerm.same_as` aligned to
FIBO, QUDT, SOSA, schema.org) makes their vocabularies interoperable by construction.

### 2.2 Data quality and misinformation
Decisions made on unverified, stale, or tampered data are worse than no decisions. Most
platforms treat quality and provenance as afterthoughts.
**Aegoria's answer:** declarative `QualityRule`s on every dataset (not_null, unique, range,
regex, enum, freshness), continuous `QualityReport`s, full upstream `LineageEdge` tracking,
and **C2PA-style content provenance signed at capture** so any derived artifact carries a
verifiable chain back to its source.

### 2.3 Surveillance vs. privacy
The dominant pattern is "collect everything, govern later." That makes mass surveillance
the path of least resistance and privacy an expensive opt-in.
**Aegoria's answer:** privacy and sovereignty are *defaults in config*, not add-ons. PII is
auto-classified, masked by default, and never exported without policy; aggregates are
answered under **(ε,δ)-differential privacy** with per-principal budget accounting;
data-residency is enforced at the engine boundary. See `PrivacyDefaults` in
`engine/aegoria_core/config.py`.

### 2.4 Energy and carbon
Big data is a large and growing source of emissions, and most query engines are
carbon-blind: they run wherever is convenient, whenever.
**Aegoria's answer:** a **carbon-aware scheduler** (the default `ComputeScheduler`) places
each query in the greenest *capable* region using live `CarbonReading`s, and the platform
reports **carbon-per-query** as a first-class KPI on the console.

### 2.5 Inequitable access
The organisations that most need data infrastructure — small NGOs, public-interest
researchers, the global South — can least afford proprietary, lock-in-heavy stacks.
**Aegoria's answer:** an OSS core that runs on a laptop (`deployment: lite`, DuckDB +
local-fs) *and* scales to a multi-cloud/edge mesh with **the same config**, plus a
participatory data-commons governance model that gives contributors a stake and a vote.
"Orgs previously excluded" is a tracked KPI.

---

## 3. The non-negotiable constraints

These are invariants. Every design decision, every PR, and every domain-pack must hold them.

1. **OSS core, no lock-in.** The core engine and contracts are open source and depend only
   on open standards. Any proprietary backend is reachable only *through* an adapter, and is
   always replaceable by an open one.

2. **The core never changes per domain or per backend.** Adding a market is a domain-pack
   plus data. Adding a cloud or a format is registering an adapter. Neither edits
   `engine.py`, `registry.py`, `config.py`, or the contracts. **This is THE invariant.**

3. **Privacy and sovereignty by default.** Differential privacy, PII masking, export
   denial, and residency enforcement are *on* unless a config explicitly relaxes them. A
   misconfiguration fails safe (more private, not less).

4. **Every decision must hold across ≥ 2 unrelated markets.** If a feature only makes sense
   for climate *or* only for credit, it does not belong in the core — it belongs in a pack.
   The two reference packs are the standing acceptance test for "is this really generic?"

5. **Open standards over bespoke formats.** Iceberg tables, OIDC identity, OPA policy, C2PA
   provenance, OpenDP privacy, Flower federation — open specs first, swappable always. See
   [Tech Stack](../architecture/tech-stack.md) for the full justification of each choice.

---

## 4. Reader's map

Start at the [documentation home](../README.md), or jump to what you need:

| Doc | What it covers | Read it if you… |
|-----|----------------|-----------------|
| [Overview](./overview.md) (this) | What Aegoria is, problems, constraints | …are new, or need the one-paragraph pitch |
| [Roadmap](./roadmap.md) | Phased, domain-independent engineering roadmap with milestones and exit criteria | …are planning, prioritising, or tracking delivery |
| [KPIs](./kpis.md) | Success KPIs: definitions, targets, measurement, console mapping | …need to know what "good" means and how it's measured |
| [Architecture](../architecture/overview.md) | Data plane, trust fabric, plugin host, topologies, query flow | …need to understand how it works |
| [Tech Stack](../architecture/tech-stack.md) | Justified open-standard tech choices + the adapter that keeps each swappable | …are evaluating technology or worried about lock-in |
| [Domain-Pack Specification](../reference/domain-pack-spec.md) | How a market onboards declaratively | …are onboarding a new market |
| [Adapter & Service Interfaces](../reference/adapter-interfaces.md) | How a new infra backend plugs in | …are adding a cloud, format, broker or IdP |
| [Access Control & RBAC](../reference/access-control-rbac.md) | Identity, roles, ABAC policies, super-admin | …are integrating auth or reasoning about access |
| [Data Commons](../governance/data-commons.md) | Participatory governance: stake, vote, proposals, sovereignty | …are a contributing community/org |
| [Brand Guidelines](../brand/guidelines.md) | Name, tagline, signature colour *Auralis*, palette, logo, voice | …are building UI, decks, or branded surfaces |

> Adjacent ground truth (read alongside the docs):
> - Contracts/vocabulary: [`engine/aegoria_core/contracts/`](../../engine/aegoria_core/contracts/)
> - The unchanging engine: [`engine/aegoria_core/engine.py`](../../engine/aegoria_core/engine.py)
> - The two reference markets: [`domain-packs/`](../../domain-packs/)
> - The console that visualises all of this: [`apps/console/`](../../apps/console/)
> - Brand assets: [`brand/`](../../brand/)
