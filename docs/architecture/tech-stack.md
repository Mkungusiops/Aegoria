# Aegoria — Tech Stack

Every technology below is chosen against the same bar from *Overview*: **open standard
first, no lock-in, swappable via an adapter or service so the core engine never changes.**

For each choice we give: **Why** it fits Aegoria, the **Open standard** it implements, the
**Alternative(s)** considered, and the **Adapter/Service** that keeps it swappable. The
adapter capability names and service names are exactly the ones the registry and config
resolve (`engine/aegoria_core/config.py`).

> Reading key: a *capability* (e.g. `storage`) is the protocol; a *provider name* (e.g.
> `local-fs`, `s3`) is a concrete implementation registered under it. Changing technology is
> changing the provider name in config — not editing the engine.

---

## 1. Table format — **Apache Iceberg**

- **Why:** open table format with ACID transactions, schema/partition evolution, hidden
  partitioning, time-travel snapshots, and broad multi-engine support. It decouples *table
  semantics* from *any single compute engine*, which is exactly the lock-in property Aegoria
  needs: the same table is readable by DuckDB on a laptop and Spark/Flink/Ray at scale.
- **Open standard:** the Apache Iceberg table spec (open, vendor-neutral, Apache-governed).
- **Alternatives:** *Delta Lake* (historically Databricks-centric; strongest inside the
  Spark/Databricks ecosystem), *Apache Hudi* (excellent for streaming upserts, but a more
  engine-coupled story). Iceberg wins on neutral multi-engine interoperability and the
  cleanest spec/catalog separation.
- **Swappable via:** the `lakehouse` **service** (default `"iceberg"`,
  `LakehouseService`). A `delta` or `hudi` lakehouse service can be registered under the same
  protocol; the engine only calls `table_location(...)` and friends.

## 2. Object storage — **S3-compatible object storage**

- **Why:** cheap, durable, infinitely scalable, and the universal substrate for lakehouse
  data. The S3 API is a de-facto open standard implemented by every major cloud and by OSS
  (MinIO, Ceph), so storage is never a hostage to one vendor.
- **Open standard:** the S3 API (de-facto), implemented by AWS S3, GCS, Azure Blob (via S3
  gateway), MinIO, Ceph.
- **Alternatives:** *POSIX/local filesystem* (used for `lite`/dev and edge), *HDFS* (legacy,
  operationally heavy). Object storage is the scale-out default; local-fs is the lite default.
- **Swappable via:** the `storage` **adapter** (`StorageAdapter`). Default `local-fs` for
  `lite`/edge; an `s3`/`gcs`/`azure` provider for scale-out. The engine only sees the
  protocol.

## 3. Streaming — **Kafka / Pulsar / Redpanda**

- **Why:** durable, partitioned, replayable event logs are the right backbone for
  sensor-streams and event-streams (e.g. climate-emissions `ground_sensors`). Aegoria stays
  neutral across the three because they share the same logical contract.
- **Open standard:** the Kafka wire protocol (de-facto open standard; Pulsar and Redpanda
  are Kafka-API-compatible). Pulsar is itself an Apache project.
- **Alternatives:** *Kafka* (richest ecosystem), *Pulsar* (native multi-tenancy, tiered
  storage, geo-replication), *Redpanda* (no-JVM, low-latency, Kafka-compatible). Each is a
  legitimate choice for different operating profiles.
- **Swappable via:** the `stream` **adapter** (`StreamAdapter`). Default `inproc` for
  `lite`/tests; a `kafka`/`pulsar`/`redpanda` provider for scale-out. Same protocol throughout.

## 4. Distributed compute — **Spark / Flink / Ray** (+ **DuckDB** for lite)

- **Why:** different jobs want different engines — Spark for large batch, Flink for true
  streaming, Ray for distributed ML/Python. Crucially, **DuckDB** gives a fully featured
  analytical engine that runs *in-process on a laptop or edge node*, which is what makes the
  `lite` and offline-first stories real. Iceberg tables let all of them read the same data.
- **Open standard:** Apache Spark and Apache Flink are Apache-governed; Ray is open source;
  DuckDB is open source (MIT). Substrait is the emerging open plan IR that helps portability
  across them.
- **Alternatives:** *Trino/Presto* (great federated SQL), *Dask* (Python-native scaling).
  All viable; the point is the platform is not wedded to any one.
- **Swappable via:** the `compute` **adapter** (`ComputeAdapter`, default `duckdb`) and the
  `scheduler` **service** (`ComputeScheduler`, default `carbon-aware`). The scheduler chooses
  *where/when* to run; the compute adapter is *how*. Register a `spark`/`flink`/`ray` compute
  provider without touching the engine.

## 5. Orchestration — **Airflow / Dagster**

- **Why:** declarative pipelines, scheduling, retries, and lineage-aware orchestration.
  Dagster's asset/typing model and Airflow's ubiquity are both well-matched to running pack
  connectors on their declared schedules (e.g. the climate `ground_sensors` `*/5 * * * *`
  cron).
- **Open standard:** both are open source (Apache Airflow is Apache-governed). The
  **OpenLineage** spec standardises the lineage they emit, which feeds Aegoria's catalog.
- **Alternatives:** *Prefect*, *Argo Workflows*, *Temporal*. Choice depends on team/runtime.
- **Swappable via:** orchestration drives the engine's `ingest`/`query` flows from outside;
  pipeline runs surface through the `catalog` **service** and lineage (`LineageEdge`). The
  core does not embed a scheduler engine, so any orchestrator can drive it.

## 6. Catalog & metadata — **DataHub / OpenMetadata**

- **Why:** searchable, governed metadata — schemas, ownership, lineage, glossary,
  classification — is what turns a pile of tables into a *findable, interoperable* commons
  (the F and I of FAIR). These projects implement open metadata models and emit/ingest
  OpenLineage.
- **Open standard:** **OpenLineage** for lineage; OpenMetadata's open metadata standard;
  both projects are open source.
- **Alternatives:** *Amundsen*, *Apache Atlas*, cloud-native catalogs (lock-in risk).
- **Swappable via:** the `catalog` **adapter** (`CatalogAdapter`, default `sql`) and the
  `catalog` **service** (default `"default"`, `CatalogService`). A `datahub`/`openmetadata`
  catalog adapter plugs in under the same protocol; the engine only calls `register`,
  `get`, `record_lineage`.

## 7. Authorization (ABAC) — **Open Policy Agent (OPA)**

- **Why:** policy-as-code, decoupled from application logic, is exactly how Aegoria expresses
  pack `AccessPolicySpec`s — attribute-based rules over principal/resource with
  deny-overrides. OPA evaluates external policy and returns an allow/deny + obligations,
  which the engine enforces without knowing the domain's *why*.
- **Open standard:** OPA is a CNCF graduated project; **Rego** is its open policy language.
  CEL-like condition expressions in `AccessPolicySpec.condition` map cleanly to it.
- **Alternatives:** *Cedar* (AWS, open-sourced), *Casbin*, hand-rolled RBAC. OPA's maturity
  and ecosystem make it the default; the protocol allows any of them.
- **Swappable via:** the `governance` **service** (`GovernanceService`, default `"default"`).
  The engine calls `authorize(request, meta) -> AccessDecision`; the policy engine behind it
  (OPA, Cedar, or the built-in evaluator) is an implementation detail.

## 8. Privacy — **OpenDP / differential privacy**

- **Why:** (ε,δ)-differential privacy gives a *quantified, provable* privacy guarantee for
  aggregates — the only honest way to publish statistics over sensitive data (consumer-credit
  aggregates run at ε = 1.0, δ = 1e-6 by default). OpenDP is a vetted, peer-reviewed library
  of DP mechanisms.
- **Open standard:** the differential-privacy mathematical framework; OpenDP (Harvard-led)
  and Google's DP libraries are open-source implementations of it. C2PA + DP together cover
  *integrity* and *confidentiality*.
- **Alternatives:** *Google DP*, *Tumult Analytics*, *SmartNoise*. All implement the same
  guarantee; the platform commits to the *guarantee*, not the library.
- **Swappable via:** DP is realised as a `differential_privacy` **obligation**
  (`Obligation`) enforced in the result path, with per-principal budgets tracked as
  `PrivacyBudget`. The mechanism library sits behind the `scheduler`/result-enforcement
  layer; swapping it changes nothing the engine sees.

## 9. Federated learning — **Flower**

- **Why:** trains models across organisations without moving raw data out of its residency
  zone — the cornerstone of Phase 3 cross-org collaboration and of sovereignty. Flower is
  framework-agnostic (works with PyTorch, TF, scikit-learn, etc.).
- **Open standard:** open-source federated-learning framework; composes with the open DP and
  C2PA standards above for private, attestable training.
- **Alternatives:** *NVIDIA FLARE*, *TensorFlow Federated*, *OpenFL*. Interchangeable for our
  needs.
- **Swappable via:** the `ml` **service** (`MLService`, default `"default"`). Pack
  `ModelSpec`s declare task/runtime; the FL backend is an ML-service implementation detail.
  The core only `register_model`s and invokes tasks.

## 10. Content provenance — **C2PA**

- **Why:** in an age of synthetic media and tampered data, every artifact must carry a
  verifiable, signed chain back to its origin. C2PA (Content Authenticity) is the open
  standard for exactly this, and it directly attacks the misinformation problem in
  *Overview*. Climate-emissions outputs ship with a watermark + provenance manifest.
- **Open standard:** the C2PA specification (Coalition for Content Provenance and
  Authenticity).
- **Alternatives:** raw detached signatures, custom manifests. C2PA standardises the manifest
  and trust model so provenance is portable and verifiable by third parties.
- **Swappable via:** the `provenance` **adapter** (`ProvenanceSigner`, default `ed25519`) and
  the `provenance` **service** (`ProvenanceService`, default `"default"`). The default uses
  Ed25519 signatures; a full C2PA signer registers under the same protocol.

## 11. Identity — **OIDC**

- **Why:** federated identity and standard claims are how principals authenticate across
  organisations — essential for cross-org federation. OIDC is the universal open standard,
  so Aegoria never builds (or owns) an identity silo.
- **Open standard:** OpenID Connect (on top of OAuth 2.0); JWT/JWKS for tokens.
- **Alternatives:** *SAML* (enterprise legacy), bespoke API keys (`static` provider for
  dev). OIDC is the interoperable default.
- **Swappable via:** the `identity` **adapter** (`IdentityAdapter`, default `static`). An
  `oidc` provider resolves principals + claims into the engine's `Principal`; the engine only
  consumes the resolved `Principal`.

## 12. Carbon intensity — **live grid carbon signals**

- **Why:** carbon-aware placement needs real per-region carbon intensity (gCO₂/kWh) to pick
  the greenest *capable* region. Aegoria treats carbon data as a pluggable source so it can
  use static estimates offline and live feeds in production.
- **Open standard:** open carbon-intensity APIs (e.g. national grid carbon-intensity APIs,
  WattTime/ElectricityMaps-style feeds) returning gCO₂/kWh per region.
- **Alternatives:** static per-region tables (the `lite` default), cloud-provider carbon
  reports.
- **Swappable via:** the `carbon` **adapter** (`CarbonSource`, default `static`) feeding the
  `carbon-aware` scheduler. Live feeds register under the same protocol; placement logic is
  unchanged.

## 13. Web console — **Next.js / React**

- **Why:** the console (`apps/console`) is the human-facing trust surface — catalog, lineage,
  governance, carbon, KPIs. Next.js (App Router) + React is the open, ubiquitous,
  server-rendered choice, with a typed `lib/` that mirrors the engine contracts.
- **Open standard:** open-source React + the web platform; communicates with the
  control-plane over plain HTTP/JSON.
- **Alternatives:** *SvelteKit*, *Remix*, *Vue/Nuxt*. Next.js chosen for ecosystem + SSR.
- **Swappable via:** the console reads from the control-plane API (`AEGORIA_API_URL`) and
  falls back to fixtures; it depends on the engine only through that HTTP contract, never on
  internals.

## 14. Engine language — **Python**

- **Why:** Python is the lingua franca of data engineering and ML, with first-class bindings
  to every technology above (PyArrow, DuckDB, Polars, PyIceberg, NumPy). It keeps the core,
  adapters, and pack hooks in one ecosystem while staying typed (pydantic models, Protocol
  contracts) and documented.
- **Open standard:** open-source CPython; Apache Arrow as the in-memory interchange standard
  across engines.
- **Alternatives:** *Rust/Java* cores (faster, but raise the contribution barrier and split
  the ecosystem). Hot paths can drop into native via Arrow without changing the contracts.
- **Swappable via:** the contracts are language-neutral protocols; a future native provider
  can implement an adapter/service so long as it honours the protocol and the Arrow data
  contract.

---

## Default provider matrix

| Capability | Kind | Lite default | Scale-out option | Standard |
|------------|------|--------------|------------------|----------|
| `storage` | adapter | `local-fs` | `s3` / `gcs` / `azure` | S3 API |
| `catalog` | adapter | `sql` | `datahub` / `openmetadata` | OpenLineage |
| `compute` | adapter | `duckdb` | `spark` / `flink` / `ray` | Arrow / Substrait |
| `stream` | adapter | `inproc` | `kafka` / `pulsar` / `redpanda` | Kafka protocol |
| `identity` | adapter | `static` | `oidc` | OpenID Connect |
| `provenance` | adapter | `ed25519` | `c2pa` | C2PA |
| `carbon` | adapter | `static` | live grid feed | carbon-intensity APIs |
| `lakehouse` | service | `iceberg` | `iceberg` (scale-out) | Iceberg spec |
| `governance` | service | `default` | OPA-backed | OPA / Rego |
| `ml` | service | `default` | Flower / FLARE | federated learning |
| `scheduler` | service | `carbon-aware` | `carbon-aware` (multi-region) | — |

**The throughline:** every row is reachable only through a protocol. Changing any cell is a
config/registration change — the engine in `engine/aegoria_core/engine.py` is never edited.
