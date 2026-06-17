# Aegoria Control Plane

The REST surface that exposes the domain-neutral **Aegoria engine** to the
[console](../apps/console). It is intentionally thin: it owns **no** domain logic
and **no** infrastructure. It bootstraps a single `AegoriaEngine` (which resolves
every adapter, service and domain-pack through the registry + declarative config),
then maps engine objects into the camelCase JSON view-models the console's
`apps/console/lib/types.ts` expects.

> Honors the core invariant: this package never imports a concrete adapter,
> service or domain-pack. Add a market by shipping a domain-pack; add a backend by
> registering an adapter. The control-plane is unchanged either way.

## Design

- **`app.py`** — the FastAPI app. On startup it calls `AegoriaEngine.bootstrap()`
  (provider discovery + config + domain-pack loading) and best-effort seeds sample
  data via `seed.py`. CORS is open for dev; responses are `orjson`-serialized.
- **`mappers.py`** — pure, total transformations from engine `snake_case` pydantic
  models to the console's `camelCase` shapes (`gco2PerKwh`, `qualityScore`,
  `piiFields`, `dpApplied`, `bytesScanned`, `recordsPerMin`, `forPct`, …).
- **`seed.py`** — optional helper that ingests each loaded pack's declared
  `sample_data` / connectors so the API serves real rows. Tolerates absence.

### Resilience

A fresh checkout may have **zero** datasets and even unresolved services (the
concrete adapters/services land in the registry from sibling packages). Every
endpoint therefore **degrades gracefully**: it returns a valid, internally
consistent (possibly empty or *derived*) payload and never `500`s on missing
engine capability. Where the engine has authoritative data (datasets, packs,
carbon, lineage) it is used; where it has no native concept (pipelines, KPIs,
governance proposals, overview aggregates) the value is derived from what is
loaded.

## Endpoints

| Method | Path                      | Returns (TS type)                       |
| ------ | ------------------------- | --------------------------------------- |
| GET    | `/health`                 | engine health + provider/registry view  |
| GET    | `/overview`               | `OverviewMetrics`                       |
| GET    | `/datasets`               | `Dataset[]`                             |
| GET    | `/datasets/{id}`          | `Dataset`                               |
| GET    | `/packs`                  | `DomainPack[]`                          |
| GET    | `/lineage`                | `{ nodes: LineageNode[]; edges: LineageEdge[] }` |
| GET    | `/policies`               | `AccessPolicy[]`                        |
| GET    | `/privacy/budgets`        | `PrivacyBudget[]`                       |
| GET    | `/carbon`                 | `CarbonReading[]`                       |
| GET    | `/queries`                | `QueryRun[]`                            |
| GET    | `/pipelines`              | `Pipeline[]`                            |
| GET    | `/graph`                  | `{ entities: GraphEntity[]; relations: GraphRelation[] }` |
| GET    | `/governance/proposals`   | `CommonsProposal[]`                     |
| GET    | `/kpis`                   | `Kpi[]`                                 |
| POST   | `/query`                  | `{ columns, rows, stats }` (QueryResult) |
| POST   | `/ingest`                 | `Dataset`                               |

`POST /query` body: `{ sql, purpose?, epsilon?, principal?, datasets? }`.
`POST /ingest` body: `{ domain, connector, source_uri, dataset, principal?, options? }`.

Authorization denials and unknown datasets/domains surface as `4xx` (not `5xx`).

## Running

The engine venv at `../engine/.venv` already has FastAPI, uvicorn and orjson.

```bash
# from repo root, with the engine importable (editable install of aegoria-core)
PYTHONPATH=engine:control-plane \
  engine/.venv/bin/python -m control_plane.cli
# or
PYTHONPATH=engine:control-plane \
  engine/.venv/bin/uvicorn control_plane.app:app --port 8000
```

Then point the console at it: `AEGORIA_API_URL=http://127.0.0.1:8000 pnpm dev`.

Environment:

- `AEGORIA_API_HOST` / `AEGORIA_API_PORT` — bind address for the CLI launcher.
- `AEGORIA_SEED=0` — disable sample-data seeding on startup.

This package is **not installed by default** (disk budget); it runs straight from
source via `PYTHONPATH`.
