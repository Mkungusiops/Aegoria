# Aegoria — Engineering Roadmap

A **phased, domain-independent** roadmap. Every phase is defined by what the *core* can do,
proven against the **two unrelated reference domains** (`climate-emissions` and
`consumer-credit`). No phase is "done" because a single market works; it is done when the
*same untouched core* serves both.

Each phase lists: **goal → milestones → exit criteria → KPIs** (KPI ids reference
*KPIs*). The invariant from *Overview* holds throughout: the core engine never
changes to add a domain or a backend.

---

## Phase 1 — Minimal Viable Lakehouse

**Goal:** an end-to-end lakehouse that is genuinely domain-neutral, proven by running two
unrelated markets through the identical core on a laptop (`deployment: lite`).

### Milestones
1. **Contracts frozen.** Data vocabulary (`contracts/models.py`), adapter protocols, service
   protocols, and the `DomainPackManifest` are stable and documented. The registry resolves
   providers by capability + name.
2. **Lite provider set.** `local-fs` storage, `sql` catalog, `duckdb` compute, `inproc`
   stream, `static` identity, `ed25519` provenance, `static` carbon — the exact default
   names the config resolves.
3. **Iceberg lakehouse service** (`lakehouse="iceberg"`) backing schema-on-read tables.
4. **Declarative ingest** of all modalities the reference packs need: structured,
   time-series, geospatial, imagery, sensor-stream — from CSV/Parquet/GeoJSON connectors.
5. **Quality + lineage at ingest.** Every declared `QualityRule` runs; every ingest writes a
   `LineageEdge`; every artifact is provenance-signed at capture.
6. **Governed query path.** `engine.query(spec, principal)` authorizes, places, executes,
   and enforces obligations — end to end.
7. **Both reference packs load and run** with zero core edits.

### Exit criteria
- [ ] `engine.bootstrap()` loads both `climate-emissions` and `consumer-credit` packs.
- [ ] A query spanning each pack's datasets returns correct results via the governed path.
- [ ] Quality reports pass on shipped sample data; lineage is queryable end-to-end.
- [ ] **Zero diffs** to `engine.py`, `registry.py`, `config.py`, or the contracts when
      adding the second pack — verified by diff.
- [ ] `engine/.venv/bin/pytest` green; `ruff` clean.

### KPIs (targets)
- `lineage` ≥ 95% upstream coverage on reference datasets.
- `quality` ≥ 0.90 average passing quality rules.
- `latency` p95 ≤ 2 s on lite (sample-scale) workloads.
- `onboard` ≤ 5 days, manifest → live, no core change (baseline measurement established here).

---

## Phase 2 — Governance & Privacy Controls

**Goal:** make the platform *trustworthy by default*. Privacy, sovereignty, and policy are
enforced as data, identically across both markets.

### Milestones
1. **ABAC/RBAC governance** evaluating pack `AccessPolicySpec`s with **deny-overrides**
   semantics, driven by the OPA-style policy adapter (see *Tech Stack*).
2. **Obligation enforcement** in the result path: `mask`, `aggregate_only` (with
   `min_group_size`), `watermark`, `residency`, and `differential_privacy`.
3. **(ε,δ)-differential privacy** on aggregates via the privacy engine, with **per-principal
   budget accounting** (`PrivacyBudget`) and config defaults ε = 1.0, δ = 1e-6.
4. **PII auto-classification** and **default masking**; export of PII denied unless policy
   explicitly allows.
5. **Data-residency enforcement** at the engine boundary (consumer-credit's
   `deny_processing_outside_eu` must actually deny).
6. **C2PA provenance manifests** on every materialised output; fairness guards for ML
   (protected-attribute exclusion + group-fairness tolerance).
7. **Transparency surfaces** wired to the console: governed-query log, privacy budgets,
   policy explanations.

### Exit criteria
- [ ] Consumer-credit: anonymous bulk export denied; analyst limited to DP aggregates;
      underwriter row access only with lawful purpose; non-EU processing denied — all proven
      by tests.
- [ ] Climate-emissions: open read succeeds *with* watermark obligation applied to outputs.
- [ ] DP budget is debited per principal and exhaustion blocks further aggregates.
- [ ] Same governance code path serves both packs — no per-domain branching in the core.

### KPIs (targets)
- `privacy` = (ε ≤ 1.0, δ = 1e-6) DP default on PII — guarantee met for 100% of aggregates.
- `quality` ≥ 0.90 sustained; PII fields protected = 100%.
- `lineage` ≥ 95% maintained as datasets grow.

---

## Phase 3 — Federated Cross-Org / Cross-Sector Sharing

**Goal:** let organisations and sectors collaborate on data they cannot or will not
centralise — sharing *insight*, not raw rows — while sovereignty holds.

### Milestones
1. **Federated query/compute**: a query is split across organisational boundaries; only
   governed, privacy-budgeted aggregates cross the wire.
2. **Federated learning** (Flower-based, swappable) so models train across orgs without data
   leaving its residency zone — exercised by consumer-credit's fairness-aware scorer and a
   multi-region climate model.
3. **Cross-org policy negotiation**: each party's `AccessPolicySpec`s compose; the strictest
   constraint wins (deny-overrides across orgs).
4. **Shared knowledge graph** linking entities across packs via aligned ontologies
   (`same_as`), enabling cross-sector joins on *meaning*, not column names.
5. **Provenance across boundaries**: C2PA chains remain verifiable when an artifact crosses
   organisations.
6. **Data-commons governance live** (see *Data Commons*): proposal
   lifecycle, contributor stake/vote, transparency dashboards.

### Exit criteria
- [ ] A cross-org aggregate over climate + a second contributor returns DP-protected results
      with **no raw rows** transferred.
- [ ] A federated model improves over any single-org model while each org's data stays in
      its residency zone.
- [ ] A commons proposal completes its full lifecycle (open → vote → enacted/rejected) and
      changes platform behaviour (e.g. a licensing or budget policy).

### KPIs (targets)
- `orgs` empowered trending up, with explicit count of previously data-poor participants.
- `sectors` live ≥ 3 (reference packs + ≥ 1 community-contributed pack).
- `privacy` guarantee preserved end-to-end across federation (no degradation vs. Phase 2).

---

## Phase 4 — Global Scale

**Goal:** the *same config-driven engine* runs as a planet-scale, multi-cloud/edge mesh that
is offline-first and carbon-optimal — and still never changed the core.

### Milestones
1. **Scale-out providers**: object storage (S3/GCS/Azure), Spark/Flink/Ray compute,
   Kafka/Pulsar/Redpanda streams, DataHub/OpenMetadata catalog — each a drop-in adapter.
2. **Multi-cloud + edge mesh**: `deployment: scaleout | edge`; carbon-aware placement spans
   regions and edge nodes using live carbon intensities.
3. **Offline-first edge**: ingest and govern locally with intermittent connectivity;
   reconcile lineage/provenance on reconnect.
4. **Carbon optimisation at scale**: greenest-capable-region placement measurably reduces
   carbon-per-query vs. naive placement, reported live.
5. **Elastic catalog + query** sustaining low p95 latency at TB-scale.
6. **Operational hardening**: multi-region residency, disaster recovery, and SLOs.

### Exit criteria
- [ ] The reference packs run unchanged on a multi-cloud deployment by **config only**
      (no code edits, no contract edits).
- [ ] Edge node ingests offline, then reconciles into the mesh with intact lineage +
      provenance.
- [ ] Carbon-aware placement demonstrably cuts carbon-per-query ≥ 60% vs. naive at scale.
- [ ] p95 query latency ≤ 2 s at TB-scale.

### KPIs (targets)
- `latency` p95 ≤ 2 s @ TB-scale.
- `carbon` ↓ ≥ 60% vs. naive placement, carbon-per-query reported per query.
- `orgs` / `sectors` continuing to grow, including offline-first edge participants.

---

## Cross-phase guardrails

- **The invariant is a release gate.** Any PR that edits the core to satisfy a domain or a
  backend is rejected; the work belongs in a pack or an adapter.
- **Two-market acceptance.** Every phase exit is validated against *both* reference packs.
- **Fail-safe privacy.** A misconfiguration must err toward *more* privacy and *stronger*
  sovereignty, never less.
- **KPIs are continuous, not milestone-only.** They are measured in CI and surfaced on the
  console at all times (see *KPIs*).
