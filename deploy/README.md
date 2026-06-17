# Aegoria — Deployment

Run the **whole app** with one command. The default stack is intentionally
**lean**: only the console and the control-plane API, built on `python:3.12-slim`
and `node:20-slim`. Heavy data infrastructure lives behind an opt-in profile.

> **THE ONE INVARIANT:** the core engine never changes. Whether you run the
> embedded laptop lakehouse or the planet-scale mesh, the same engine resolves
> different *providers* from the registry. Deployment is purely a packaging
> concern.

## Prerequisites

- Docker with Compose v2 (`docker compose`, not `docker-compose`).
- Run commands **from the repo root** — the Dockerfiles use the repo root as the
  build context (set as `context: ..` in the compose file) so the images can see
  `engine/`, `control-plane/`, `sdk/`, `domain-packs/` and `apps/console/`.

## Run the app (default lean stack)

```sh
docker compose -f deploy/docker-compose.yml up --build
```

Then open:

- **Console (UI):** http://localhost:3000
- **API (control-plane):** http://localhost:8000 — health at
  http://localhost:8000/health

The console serves built-in fixtures, so the UI is **guaranteed to render** even
before the API is healthy. To drive the console from the **live engine** instead,
uncomment the `AEGORIA_API_URL=http://api:8000` line under the `console` service
in `deploy/docker-compose.yml` and re-run `up`.

### What you get

| Service   | Image base         | Port   | Notes                                        |
| --------- | ------------------ | ------ | -------------------------------------------- |
| `console` | `node:20-slim`     | `3000` | Next.js standalone; fixtures by default.     |
| `api`     | `python:3.12-slim` | `8000` | FastAPI + embedded `lite` lakehouse engine.  |

The API persists its warehouse to `./.aegoria` on the host (a bind-mounted
volume). Set `AEGORIA_SEED=1` on the `api` service to seed sample data on boot.

## Stop / logs

```sh
docker compose -f deploy/docker-compose.yml down       # stop + remove
docker compose -f deploy/docker-compose.yml logs -f    # follow logs
```

Or via the root `Makefile`: `make up`, `make down`, `make logs`.

## Scale-out mesh (opt-in `scaleout` profile)

The `scaleout` profile adds real, distributed infrastructure that the engine's
adapters/services can be pointed at — **without changing the engine**. These
images are **not pulled or started by default**.

```sh
docker compose -f deploy/docker-compose.yml --profile scaleout up
```

| Service        | Maps to Aegoria provider                | Ports        |
| -------------- | --------------------------------------- | ------------ |
| `minio`        | `StorageAdapter` (S3 object store)      | 9000 / 9001  |
| `iceberg-rest` | `LakehouseService "iceberg"` (REST)     | 8181         |
| `nessie`       | `CatalogAdapter` (versioned catalog)    | 19120        |
| `spark`        | `ComputeAdapter "spark"`                | 7077 / 8080  |
| `trino`        | `ComputeAdapter "trino"` (federated SQL) | 8081         |
| `redpanda`     | `StreamAdapter "kafka"` (Kafka API)     | 9092 / 9644  |
| `dagster`      | `ComputeScheduler` (orchestration UI)   | 3030         |

To actually route the engine through these, register/select the matching
provider names in `AegoriaConfig` (e.g. `storage="s3"`, `compute="spark"`,
`stream="kafka"`) and supply the endpoints above as adapter options. The default
lean stack uses the embedded providers and pulls none of these images.

## Kubernetes & the hybrid multi-cloud / edge mesh

Manifests and the full mesh + offline-first edge design live in
[`deploy/k8s/`](./k8s/README.md): namespace, console + API deployments/services,
ingress, and a `HorizontalPodAutoscaler`.

## Files

| File                     | Purpose                                                      |
| ------------------------ | ------------------------------------------------------------ |
| `Dockerfile.console`     | Multi-stage Next.js standalone build (context = repo root).  |
| `Dockerfile.api`         | `python:3.12-slim` control-plane + embedded engine.          |
| `api-entrypoint.sh`      | Optional sample-data seed, then `exec` uvicorn.              |
| `docker-compose.yml`     | Lean default stack + opt-in `scaleout` profile.              |
| `.dockerignore`          | Keeps the (repo-root) build context small.                   |
| `k8s/`                   | Kubernetes manifests + mesh / edge design notes.             |
