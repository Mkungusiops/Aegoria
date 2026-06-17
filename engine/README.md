# aegoria-core

The domain-neutral, privacy-preserving big-data engine at the heart of **Aegoria**.

`aegoria-core` is an open-table-format lakehouse platform that makes **no assumptions
about its domain**. It ingests heterogeneous, multi-modal data (structured records,
imagery, IoT/sensor streams, text, time-series, geospatial, real-time events) into an
Apache Iceberg lakehouse over object storage, attaches machine-readable provenance,
lineage and licensing at the moment of capture, governs every byte with a privacy-first
trust fabric (PII classification, ABAC/RBAC, differential privacy, federated learning),
and executes governed queries on a **carbon-aware scheduler** that places work on the
greenest capable engine.

## The one idea

> **The core engine never changes.** Infrastructure is swapped via *adapters*
> (storage, catalog, compute, streaming, identity, provenance, carbon). Markets are
> onboarded via declarative, versioned *domain-packs* (schemas, ontology, quality rules,
> ML models, access policy). The engine binds only to stable protocols and resolves
> concrete providers from a registry — so a new cloud, lake format, broker, IdP, or
> entire industry is added with **zero edits to engine code**.

```python
from aegoria_core import AegoriaEngine

engine = AegoriaEngine.bootstrap()          # reads aegoria.yaml, discovers providers, loads packs
engine.health()                              # wired adapters/services + loaded domain-packs
```

## Layout

| Path | What it is | Stability |
|------|------------|-----------|
| `aegoria_core/contracts/` | Models + adapter/service/domain-pack **protocols** | Frozen core |
| `aegoria_core/engine.py`  | `AegoriaEngine` orchestrator (imports no concrete provider) | Frozen core |
| `aegoria_core/registry.py`| Provider registry + entry-point discovery | Frozen core |
| `aegoria_core/services/`  | Default domain-neutral service impls (lakehouse, ingestion, governance, scheduler, …) | Swappable |
| `../adapters/`            | Infra adapters (local-fs, iceberg, duckdb, kafka, oidc, …) | Swappable |
| `../domain-packs/`        | Declarative markets (climate-emissions, consumer-credit, …) | Swappable |

## Install (embedded / lite)

```bash
uv venv && uv pip install -e ".[lite,api,ml,privacy,dev]"
aegoria doctor          # show wired providers + loaded packs
aegoria packs           # list onboarded markets
```

The **lite** profile runs a complete lakehouse on a laptop (PyIceberg SQL catalog +
local warehouse, DuckDB/Polars/Arrow compute). The **scale-out** profile swaps the same
adapters for MinIO/S3 + Iceberg REST + Nessie, Spark/Trino, and Redpanda — see
`../deploy/`.

Licensed Apache-2.0.
