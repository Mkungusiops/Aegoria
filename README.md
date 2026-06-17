<div align="center">

<img src="brand/logo-wordmark.svg" alt="Aegoria" width="340" />

### One planet. Every domain. Data you can trust.

**Aegoria** is a planet-scale, **market-agnostic**, privacy-preserving **big-data lakehouse platform**.
The core engine never changes — infrastructure is swapped via *adapters*, and entire
industries onboard as declarative, versioned *domain-packs*.

`climate emissions` · `consumer credit` · `population health` · `multimodal freight` · *…your market next*

</div>

---

## The one idea

> **The core engine never changes when you add a market or a cloud.**
>
> - **Infrastructure** (object storage, table catalog, compute, streaming, identity, provenance, carbon) sits behind **adapter protocols**. A laptop’s DuckDB + local-FS warehouse and a planetary Spark + MinIO + Iceberg-REST + Redpanda mesh implement the *same* interfaces.
> - **Markets** onboard as **domain-packs**: portable YAML manifests carrying schemas, ontologies, quality rules, ML-model references and access policy — *as data*, never as engine code.
> - The engine binds only to stable **protocols** and resolves concrete providers from a **registry** via entry points. Adding a backend or a whole industry means shipping a plugin, with **zero edits to engine code**.

This invariant is mechanically enforced and proven by a test that drives **two deliberately unrelated markets** (geospatial climate emissions vs. PII-heavy consumer credit) through one branchless code path and asserts the core source is byte-stable (`engine/tests/test_domain_neutrality.py`).

## What it does, end to end

```
ingest (multi-modal) ─▶ Iceberg lakehouse (schema-on-read, open formats)
        │                        │
   provenance + lineage     FAIR catalog + knowledge graph (entity resolution)
   attached AT CAPTURE           │
        ▼                        ▼
   TRUST FABRIC ───────▶ CARBON-AWARE COMPUTE ───────▶ governed results
   PII classification     greenest-grid placement       (authorize → place →
   ABAC/RBAC · residency  DuckDB / Spark / Trino / Ray   execute → enforce
   differential privacy                                  privacy obligations)
   federated learning · C2PA signing
```

Every query is **authorized** (ABAC/RBAC + data residency), **placed on the greenest capable region**, **executed**, then has **privacy obligations enforced** (masking, aggregate-only, differential privacy) *before* a single row is returned.

## Quickstart

### ▶︎ Run the whole platform with Docker (recommended)

```bash
docker compose -f deploy/docker-compose.yml up --build
```

This builds and runs two lean services and seeds the embedded lakehouse with real sample data for both reference domains:

| Service | URL | What it is |
|--------|-----|------------|
| **Console** | http://localhost:3000 | The enterprise UI (Next.js) |
| **API** | http://localhost:8000 | Control-plane (FastAPI) over the live engine — try http://localhost:8000/docs |

Verify the **live** engine (real Iceberg data, governance, carbon-aware placement, differential privacy):

```bash
# Governed + carbon-aware aggregate on open climate data
curl -s localhost:8000/datasets | jq '.[].id'
curl -s -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"sql":"SELECT count(*) facilities, round(sum(co2e_tonnes)) total FROM facility_emissions","purpose":"demo"}'

# Differential-privacy aggregate on credit data — as an EU analyst (residency-allowed)
curl -s -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"sql":"SELECT decision, count(*) n, round(avg(income)) avg_income FROM loan_applications GROUP BY decision",
       "epsilon":1.0,"roles":["analyst"],"jurisdiction":"EU","attributes":{"purpose":"underwriting"}}'

# Raw PII pull — DENIED by the privacy fabric (HTTP 403)
curl -i -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"sql":"SELECT applicant_name, national_id, email FROM loan_applications LIMIT 5","roles":["analyst"],"jurisdiction":"EU"}'
```

> The console renders a complete, beautiful UI from built-in fixtures by default. To drive it from the **live** engine instead, set `AEGORIA_API_URL: http://api:8000` on the `console` service in `deploy/docker-compose.yml`.

**Scale-out (opt-in):** the same adapters point at real infra — MinIO/S3, Iceberg-REST, Nessie, Spark, Trino, Redpanda (Kafka), Dagster — without touching the core:

```bash
docker compose -f deploy/docker-compose.yml --profile scaleout up
```

### ▶︎ Run the engine + lakehouse demo locally (no Docker)

```bash
cd engine && uv venv && uv pip install -e ".[lite,api,ml,privacy,dev]"
aegoria doctor                       # show wired providers + loaded domain-packs
python ../examples/e2e_demo.py       # ingest both domains → govern → DP → carbon → provenance
pytest ../engine/tests -q            # 31 tests
```

### ▶︎ Run the console in dev mode

```bash
pnpm install
pnpm --filter @aegoria/console dev   # http://localhost:3000
```

Or use the `Makefile`: `make up`, `make demo`, `make console-dev`, `make api-dev`, `make down`.

## What’s verified

- ✅ **31 engine tests pass**, including the domain-neutrality proof (one core, two unrelated markets, zero core edits).
- ✅ **End-to-end demo** ingests both domains into an Iceberg lakehouse with provenance + C2PA-style signatures attached at capture, runs governed carbon-aware queries, enforces differential privacy, and verifies signatures (incl. tamper rejection).
- ✅ **Console production build** — 13 routes, all green.
- ✅ **Docker stack** — console + API both healthy; API serves **real** seeded lakehouse data; governance demonstrably allows EU DP aggregates and denies raw-PII pulls and non-EU residency.

## Repository layout

| Path | What it is |
|------|------------|
| [`engine/`](engine/) | **`aegoria-core`** — frozen contracts (`contracts/`), registry, `AegoriaEngine`, and the lite reference services + built-in adapters |
| [`adapters`](engine/aegoria_core/adapters_builtin/) · [`services`](engine/aegoria_core/services/) | Built-in infra adapters (local-fs, sql/Iceberg, DuckDB, in-proc, OIDC-static, ed25519, carbon) + domain-neutral services (lakehouse, ingestion, catalog, governance, scheduler, knowledge-graph, ML, provenance) |
| [`domain-packs/`](domain-packs/) | The two unrelated reference markets: [`climate-emissions/`](domain-packs/climate-emissions/) and [`consumer-credit/`](domain-packs/consumer-credit/) |
| [`control-plane/`](control-plane/) | FastAPI control-plane exposing the engine to the console |
| [`sdk/`](sdk/) | **`aegoria-sdk`** — author/validate/test new domain-packs; `aegoria-pack` CLI |
| [`apps/console/`](apps/console/) | The enterprise UI (Next.js 15 + React 19 + Tailwind) |
| [`deploy/`](deploy/) | Dockerfiles, `docker-compose.yml` (lite + scaleout), and `k8s/` (hybrid multi-cloud / edge mesh) |
| [`examples/`](examples/) | `e2e_demo.py` narrated end-to-end run |
| [`docs/`](docs/) | Sectioned documentation: product, architecture (+ ADRs), reference, governance, brand |
| [`brand/`](brand/) | Logo, wordmark, favicon, design tokens |

## Documentation

Start at the **[documentation home](docs/README.md)**. The docs are organized into sections:

| Section | Contents |
|---------|----------|
| [Product](docs/product/) | [Overview](docs/product/overview.md) · [Roadmap](docs/product/roadmap.md) · [KPIs](docs/product/kpis.md) — what & why, the plan, and how success is measured |
| [Architecture](docs/architecture/) | [Overview](docs/architecture/overview.md) · [Tech Stack](docs/architecture/tech-stack.md) · [Decisions (ADRs)](docs/architecture/decisions/) — how it works + the decisions of record |
| [Reference](docs/reference/) | [Domain-Pack Spec](docs/reference/domain-pack-spec.md) · [Adapter & Service Interfaces](docs/reference/adapter-interfaces.md) · [Access Control & RBAC](docs/reference/access-control-rbac.md) |
| [Governance](docs/governance/) | [Data Commons](docs/governance/data-commons.md) · [Security & Compliance](docs/governance/security.md) |
| [Brand](docs/brand/) | [Guidelines](docs/brand/guidelines.md) — the signature colour *Auralis*, logo, voice |
| [Glossary](docs/GLOSSARY.md) | Canonical vocabulary used across all docs |

## Tech stack (open standards, no lock-in)

Apache **Iceberg** lakehouse over object storage · **Kafka/Pulsar/Redpanda** streaming · **Spark/Flink/Ray** + **DuckDB** compute on a **carbon-aware** scheduler · **DataHub/OpenMetadata**-style FAIR catalog · **OPA**-style ABAC · **differential privacy** + **federated learning** · **C2PA** provenance · **OIDC** identity · **Next.js/React** · **Python** core. Open-source core, Apache-2.0.

## Brand

The signature colour is **Auralis `#16E0C4`** — a living cyan-jade, *the colour of data becoming knowledge* — on the deep **Veil** canvas, with **Pulse** violet (compute/AI) and **Verdant** green (carbon). The mark is an **aperture of three converging arcs around a luminous core**: many domains resolving into one trusted lens. See [docs/brand/guidelines.md](docs/brand/guidelines.md).

---

<div align="center"><sub>Aegoria · open-source core · privacy & data sovereignty by default · built to hold across every market.</sub></div>
