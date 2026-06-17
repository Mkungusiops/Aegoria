# Aegoria on Kubernetes — the hybrid multi-cloud / edge mesh

These manifests deploy the **lean** Aegoria control surface (console + API) and
let it grow into a **planet-scale, hybrid multi-cloud and edge mesh** — all
without ever changing the core engine. Infra is swapped via adapters; markets
onboard via domain-packs; the engine resolves providers from a registry. The
deployment topology is therefore *purely a packaging concern*.

## What's here

| File             | Purpose                                                             |
| ---------------- | ------------------------------------------------------------------- |
| `namespace.yaml` | The `aegoria` namespace, labelled for mesh tier placement.          |
| `api.yaml`       | Control-plane API `Deployment` + `Service` (FastAPI over the engine). |
| `console.yaml`   | Next.js console `Deployment` + `Service` (standalone, fixture-backed). |
| `ingress.yaml`   | Single ingress: console at `/`, API under `/api`.                   |
| `hpa.yaml`       | `HorizontalPodAutoscaler` for the API request-serving tier.         |

## Quick start (single cluster)

```sh
# Build + push the images (build context MUST be the repo root):
docker build -f deploy/Dockerfile.api      -t <registry>/aegoria-api:latest     .
docker build -f deploy/Dockerfile.console  -t <registry>/aegoria-console:latest .
docker push <registry>/aegoria-api:latest
docker push <registry>/aegoria-console:latest

# Point the manifests at your images (edit the `image:` fields), then:
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/api.yaml
kubectl apply -f deploy/k8s/console.yaml
kubectl apply -f deploy/k8s/hpa.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

The console renders from built-in fixtures by default. To drive it from the
live engine, uncomment `AEGORIA_API_URL` in `console.yaml` (it resolves the API
`Service` DNS name `http://aegoria-api:8000` inside the namespace).

## The hybrid multi-cloud / edge mesh

Aegoria is designed to span clouds and the edge as **one logical platform** made
of many physically independent cells. There is exactly one invariant: **the core
engine binary is identical everywhere** — only the registered providers differ.

```
                           ┌────────────────────────────┐
                           │   Global control-plane      │
                           │   (governance, catalog,     │
                           │    lineage, privacy budget) │
                           └───────────────┬─────────────┘
                                           │  signed, privacy-preserving
                                           │  metadata + policy sync
        ┌──────────────────────┬───────────┴───────────┬──────────────────────┐
        ▼                      ▼                        ▼                      ▼
 ┌─────────────┐       ┌─────────────┐          ┌─────────────┐        ┌─────────────┐
 │ Cloud cell A│       │ Cloud cell B│          │ Region cell │        │  Edge cell  │
 │  (e.g. AWS) │       │  (e.g. GCP) │          │ (sovereign) │        │ (on-prem /  │
 │             │       │             │          │             │        │  offline)   │
 │ s3 storage  │       │ gcs storage │          │ local-fs +  │        │ local-fs +  │
 │ iceberg-rest│       │ iceberg-rest│          │ sql catalog │        │ sql catalog │
 │ spark/trino │       │ spark/trino │          │ duckdb      │        │ duckdb      │
 │ kafka bus   │       │ kafka bus   │          │ inproc bus  │        │ inproc bus  │
 └─────────────┘       └─────────────┘          └─────────────┘        └─────────────┘
```

### How the same engine runs in every cell

- **Storage / catalog / compute / stream** are reached only through
  `StorageAdapter`, `CatalogAdapter`, `ComputeAdapter`, `StreamAdapter`. A cloud
  cell registers `storage="s3"` + `compute="spark"`; an edge cell registers
  `storage="local-fs"` + `compute="duckdb"`. The engine code is byte-identical.
- **Services** (`lakehouse`, `governance`, `scheduler`, …) likewise resolve from
  the registry. A cell can run the embedded `iceberg` lakehouse service backed by
  an Iceberg REST catalog in the cloud, or the same service backed by SQLite at
  the edge.
- **Domain-packs** are declarative manifests synced to every cell, so a market
  onboarded once is available mesh-wide without code changes.

### Data residency & sovereignty

`Jurisdiction` on every `DatasetMetadata` plus `AccessPolicySpec` obligations let
the governance service pin sensitive datasets to specific cells. The global
control-plane only ever exchanges **signed metadata, lineage and policy** (never
raw rows), so a sovereign or air-gapped cell can participate without exporting
regulated data. `PrivacyBudget` is tracked per principal and reconciled centrally
so differential-privacy spend is consistent across the whole mesh.

### Carbon-aware placement

The `carbon-aware` `ComputeScheduler` reads each cell's `CarbonSource` and shifts
deferrable batch work toward the greenest cell/time window. The API tier scales
with the `HorizontalPodAutoscaler`; batch work is shaped by the scheduler. Add a
node label such as `aegoria.io/carbon-intensity` and a `nodeAffinity` /
topology-spread rule to bias pods toward low-carbon zones.

## Offline-first edge clients

Edge cells are built to run **disconnected** and reconcile when a link returns:

1. **Self-contained image.** The API image ships the embedded `lite` lakehouse
   (DuckDB + PyIceberg-on-SQLite + Polars/pyarrow) and `local-fs` storage — no
   cloud dependency to boot or serve. An edge box runs the full engine locally.
2. **Local-first writes.** Ingestion, queries and the knowledge graph operate
   against the local warehouse (the `warehouse` volume / PVC). Latency-sensitive
   workloads never round-trip to the cloud.
3. **Durable outbox + CRDT-style sync.** Each cell records signed `Provenance`
   and `Lineage` for everything it writes into a local outbox. On reconnect it
   pushes that **metadata** (not raw data) to the global control-plane and pulls
   the latest policies/domain-packs/catalog deltas. Conflicts are resolved by
   last-writer-wins on immutable, content-addressed dataset versions, so sync is
   idempotent and partition-tolerant.
4. **Policy stays enforced offline.** Because `GovernanceService` and the cached
   `AccessPolicySpec`/`Obligation` set live in the cell, access decisions and
   privacy-budget accounting keep working with no connectivity; spend is
   reconciled with the global budget on the next sync.
5. **Graceful upgrade path.** When an edge cell gains durable infra it simply
   re-registers heavier providers (`storage="s3"`, `compute="spark"`); the engine
   and all domain-packs are unchanged — only the registry bindings move.

### Deploying an edge cell

Use the same manifests, but:

- Run `aegoria-api` as a single replica (or a `DaemonSet` for one-per-node) with
  a `PersistentVolumeClaim` instead of the `emptyDir` so the local warehouse
  survives restarts.
- Drop the `HorizontalPodAutoscaler` (edge nodes are fixed-capacity).
- Keep the console for a fully local operator UI; it needs no cloud link.
- Schedule onto edge nodes with a `nodeSelector` such as
  `aegoria.io/tier: edge` and tolerations for intermittent nodes.
