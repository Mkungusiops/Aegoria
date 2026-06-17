"""End-to-end smoke test for the lite reference implementation.

Bootstraps a fully-wired engine over a temp warehouse, writes an Arrow table via
the lakehouse, scans it back, runs an aggregate query through the carbon-aware
scheduler (asserting non-zero carbon accounting), and proves a PII ``mask``
obligation actually redacts a column.
"""

from __future__ import annotations

import pyarrow as pa
import pytest

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts.models import (
    DatasetMetadata,
    DatasetRef,
    FieldSchema,
    FieldType,
    Obligation,
    QuerySpec,
    Sensitivity,
    TableSchema,
)


def _config(tmp_path) -> AegoriaConfig:
    warehouse = tmp_path / "warehouse"
    catalog_db = tmp_path / "catalog.db"
    return AegoriaConfig(
        warehouse_uri=str(warehouse),
        catalog_uri=f"sqlite:///{catalog_db}",
        domain_pack_paths=[],
    )


def _schema() -> TableSchema:
    return TableSchema(
        name="customers",
        fields=[
            FieldSchema(name="id", type=FieldType.LONG, nullable=False),
            FieldSchema(name="email", type=FieldType.STRING, sensitivity=Sensitivity.PII, pii=True),
            FieldSchema(name="amount", type=FieldType.DOUBLE),
        ],
    )


@pytest.fixture()
def engine(tmp_path) -> AegoriaEngine:
    return AegoriaEngine.bootstrap(_config(tmp_path))


def test_health_wires_all_providers(engine: AegoriaEngine) -> None:
    providers = engine.health()["providers"]
    assert set(providers["adapters"]) >= {
        "storage", "catalog", "compute", "stream", "identity", "provenance", "carbon"
    }
    assert set(providers["services"]) >= {
        "lakehouse", "ingestion", "catalog", "governance",
        "scheduler", "knowledge_graph", "ml", "provenance",
    }


def test_lakehouse_write_scan_query_carbon_and_mask(engine: AegoriaEngine) -> None:
    schema = _schema()
    ref = DatasetRef(domain="demo", name="customers", version="1.0.0")
    meta = DatasetMetadata(
        ref=ref,
        title="Customers",
        schema=schema,
        owner="alice",
    )

    # 1. create + write via the lakehouse service
    engine.lakehouse.create_table(meta)
    table = pa.table(
        {
            "id": [1, 2, 3, 4],
            "email": ["a@x.com", "b@y.com", "c@z.com", "d@w.com"],
            "amount": [10.0, 20.0, 30.0, 40.0],
        }
    )
    written = engine.lakehouse.write(ref, table, mode="append")
    assert written == 4

    # 2. scan it back
    scanned = engine.lakehouse.scan(ref)
    assert scanned.num_rows == 4
    assert set(scanned.column_names) == {"id", "email", "amount"}

    # register classified metadata so engine.query() can authorize it
    engine.catalog.register(engine.governance.classify(meta, sample=table))

    # 3. aggregate query through engine.query() -> carbon accounting
    spec = QuerySpec(
        sql="SELECT count(*) AS n, sum(amount) AS total FROM customers",
        datasets=[ref],
        purpose="test",
    )
    result = engine.query(spec)
    assert result.stats.rows == 1
    row = result.rows[0]
    assert result.stats.engine == "duckdb"
    assert result.stats.carbon_g > 0
    assert result.stats.energy_kwh > 0
    # The anonymous principal is not the owner and the dataset has PII, so
    # differential privacy is applied by default: numeric aggregates carry
    # calibrated Laplace noise but stay close to the true value.
    assert result.stats.dp_applied is True
    assert result.stats.epsilon_spent > 0
    assert row["total"] == pytest.approx(100.0, abs=20.0)
    assert row["n"] == pytest.approx(4, abs=20.0)

    # 4. PII mask obligation redacts the email column
    masked = engine.governance.apply_obligations(
        table,
        [Obligation(kind="mask", params={"fields": ["email"], "strategy": "hash"})],
        schema=schema,
    )
    masked_emails = masked.column("email").to_pylist()
    assert "a@x.com" not in masked_emails
    assert all("@" not in v for v in masked_emails)
    # non-PII columns untouched
    assert masked.column("amount").to_pylist() == [10.0, 20.0, 30.0, 40.0]
