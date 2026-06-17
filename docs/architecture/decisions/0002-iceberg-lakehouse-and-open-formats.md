# 0002 — Iceberg lakehouse over open formats

- **Status:** Accepted
- **Date:** 2026-06-17
- **Deciders:** Platform architecture, data engineering
- **Related:** [Architecture · Tech Stack](../tech-stack.md), [0004 — Provider-agnostic adapters](./0004-provider-agnostic-adapters-and-plugins.md)

## Context

Aegoria ingests heterogeneous, multi-modal data (structured, imagery, IoT/sensor streams,
text, time-series, geospatial, events) and must serve it for analytics and ML at planet
scale, while remaining **vendor-neutral** and **schema-on-read** (each domain defines its own
schemas). It must run on a laptop for under-connected regions *and* scale to a multi-cloud
mesh — without rewriting the data layer.

## Decision

Adopt an **open-table-format lakehouse** over object storage as the storage substrate, with
**Apache Iceberg** as the default table format and **Apache Arrow/Parquet** as the in-memory
and on-disk columnar formats. Compute is pluggable: **DuckDB** for the embedded/lite path,
**Spark/Trino** (and Ray) for scale-out — all reading the same Iceberg tables. Streaming uses
the **Kafka API** (Redpanda/Kafka/Pulsar).

The lakehouse sits behind the `LakehouseService` + `StorageAdapter` + `CatalogAdapter`
[protocols](../../../engine/aegoria_core/contracts/), so the format is itself swappable.

## Consequences

**Positive**
- Open spec, broad engine support (Spark, Trino, DuckDB, Flink, Dremio…) — no lock-in.
- Schema evolution, hidden partitioning, snapshots/time-travel, and ACID commits out of the box.
- Same tables, same code, from laptop (SQLite catalog + local FS) to cloud (REST catalog + S3).

**Negative / costs we accept**
- Iceberg metadata + catalog adds operational surface vs. plain Parquet directories.
- The lite path constrains some scale-out features to keep a laptop install small.

**Neutral**
- Delta Lake / Hudi remain viable behind the same `LakehouseService` protocol if a deployment prefers them.

## Alternatives considered

- **A proprietary warehouse (e.g. a single-vendor cloud DW)** — fast to start, but lock-in and
  no offline/edge story; violates the no-lock-in constraint.
- **Plain Parquet on object storage** — no ACID, no schema evolution, no snapshots; pushes that
  complexity into every consumer.
- **Delta Lake as default** — excellent, but Iceberg's catalog-neutrality and multi-engine
  reach fit the vendor-neutral goal slightly better; kept as a swappable option.
