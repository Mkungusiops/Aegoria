"""Tests for the data-onboarding capability: connect → assess → clean → AI-ready.

Exercises the new ``source`` connectors and the ``dataprep`` studio entirely
through their public surface, against deliberately *dirty* fixtures (duplicate
rows, blanks/sentinels, stray whitespace, inconsistent casing, numbers stored as
text, packed value+unit, and real PII). Asserts that:

* the source connectors read honestly (all-string CSV, richest SQLite table,
  truncation accounting),
* assessment detects each class of dirtiness and classifies PII via governance,
* cleaning trims/null-normalizes/coerces/dedupes and improves the quality score,
* the AI bundle masks PII (no raw value leaks) and is provenance-signed,
* onboarding writes cleaned Parquet/CSV/report and lands a governed dataset,
* the whole capability is registered as plugins (zero engine edits).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.contracts.models import DatasetRef
from aegoria_core.dataprep import get_studio
from aegoria_core.dataprep.cleanser import apply_plan, derive_plan

DIRTY_CSV = """id,customer,email,amount,weight,country,joined
1,  Ada  ,ada@example.com,1200.50,90 KG,United Kingdom,2021-01-05
2,Alan,alan@example.com,980,50 KG,uk,2021-02-11
3,Grace,grace@example.com,NA,90 KG,USA,2021-03-02
3,Grace,grace@example.com,NA,90 KG,USA,2021-03-02
4,Kath,kath@example.com,2310,50 KG,usa,2021-04-18
5,Edsger,,,,Netherlands,
6,Margaret,maggie@example.com,47999,90 KG,netherlands,2021-06-30
"""


@pytest.fixture()
def engine(tmp_path) -> AegoriaEngine:
    cfg = AegoriaConfig(
        warehouse_uri=str(tmp_path / "warehouse"),
        catalog_uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        domain_pack_paths=[],
    )
    return AegoriaEngine.bootstrap(cfg)


@pytest.fixture()
def studio(engine):
    return get_studio(engine)


@pytest.fixture()
def dirty_csv(tmp_path) -> Path:
    p = tmp_path / "customers.csv"
    p.write_text(DIRTY_CSV)
    return p


@pytest.fixture()
def dirty_db(tmp_path) -> Path:
    p = tmp_path / "app.sqlite"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE tiny (k TEXT)")
    con.execute("INSERT INTO tiny VALUES ('x')")
    con.execute(
        "CREATE TABLE customers (id TEXT, customer TEXT, email TEXT, amount TEXT, country TEXT)"
    )
    con.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        [
            ("1", " Ada ", "ada@example.com", "1200.50", "USA"),
            ("2", "Alan", "alan@example.com", "NA", "usa"),
            ("2", "Alan", "alan@example.com", "NA", "usa"),
        ],
    )
    con.commit()
    con.close()
    return p


# --------------------------------------------------------------------------- #
# Registration / plugin wiring
# --------------------------------------------------------------------------- #
def test_capability_registered_as_plugins(engine):
    desc = engine.registry.describe()
    assert set(desc["adapters"]["source"]) >= {"file", "sqlite", "sql"}
    assert "studio" in desc["adapters"]["dataprep"]


# --------------------------------------------------------------------------- #
# Source connectors
# --------------------------------------------------------------------------- #
def test_file_connector_reads_all_string_and_preserves_blanks(studio, dirty_csv):
    table, desc = studio.connect(str(dirty_csv))
    assert desc.connector == "file"
    assert table.num_rows == 7
    # All columns read as text so dirtiness survives to the profiler.
    assert all(str(table.schema.field(n).type) == "string" for n in table.column_names)
    # The empty amount cell stays "" (a blank), not a null.
    assert "" in table.column("amount").to_pylist()


def test_file_connector_truncation_accounting(studio, dirty_csv):
    table, desc = studio.connect(str(dirty_csv), limit=3)
    assert table.num_rows == 3
    assert desc.row_estimate == 7
    assert desc.truncated is True


def test_sqlite_connector_picks_richest_table(studio, dirty_db):
    assert set(studio.list_tables(str(dirty_db))) == {"tiny", "customers"}
    table, desc = studio.connect(str(dirty_db))
    assert desc.connector == "sqlite"
    assert desc.table == "customers"  # 3 rows beats tiny's 1
    assert table.num_rows == 3


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #
def test_assess_detects_dirtiness_and_pii(studio, dirty_csv):
    report = studio.assess(str(dirty_csv), dataset="customers")
    assert report.duplicate_rows == 1
    cols = {c.name: c for c in report.columns}

    # numbers-as-text
    assert cols["id"].inferred_type == "int"
    assert "coerce_type" in cols["id"].recommended_steps
    assert cols["amount"].inferred_type == "double"

    # whitespace + blanks
    assert cols["customer"].whitespace_count >= 1
    assert cols["amount"].null_fraction > 0  # NA + "" treated as missing

    # packed value+unit
    assert cols["weight"].embedded_unit == "KG"
    assert "split_unit" in cols["weight"].recommended_steps

    # inconsistent category casing
    assert cols["country"].near_duplicate_categories

    # PII via the engine's governance classifier
    assert "email" in report.pii_columns
    assert report.has_pii


def test_recommended_plan_has_expected_ops(studio, dirty_csv):
    report = studio.assess(str(dirty_csv), dataset="customers")
    ops = [s.op for s in report.recommended_plan.steps]
    for expected in ("trim", "empty_to_null", "coerce_type", "dedupe_rows"):
        assert expected in ops


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def test_clean_trims_dedupes_coerces_and_improves_quality(studio, dirty_csv):
    cleaned, result, report = studio.clean(str(dirty_csv), dataset="customers")
    # dedupe removed the exact duplicate row
    assert result.output_rows == report.sampled_rows - 1
    # types were coerced
    types = {f.name: str(f.type) for f in cleaned.schema}
    assert types["id"] == "int64"
    assert types["amount"] == "double"
    # whitespace trimmed
    assert " Ada " not in cleaned.column("customer").to_pylist()
    assert "Ada" in cleaned.column("customer").to_pylist()
    # sentinel "NA" became null
    assert "NA" not in [v for v in cleaned.column("amount").to_pylist()]
    # cleaning did not make quality worse
    assert result.output_quality_score >= result.input_quality_score


def test_split_unit_creates_value_and_unit_columns(studio, dirty_csv):
    cleaned, result, _ = studio.clean(str(dirty_csv), dataset="customers")
    assert "weight_value" in cleaned.column_names
    assert "weight_unit" in cleaned.column_names
    assert "weight" not in cleaned.column_names
    assert 90.0 in cleaned.column("weight_value").to_pylist()
    assert "KG" in cleaned.column("weight_unit").to_pylist()


def test_normalize_collapses_case_duplicates(studio, dirty_csv):
    cleaned, *_ = studio.clean(str(dirty_csv), dataset="customers")
    countries = set(cleaned.column("country").to_pylist())
    # "USA"/"usa" and "Netherlands"/"netherlands" must not both survive.
    assert not ({"USA", "usa"} <= countries)
    assert not ({"Netherlands", "netherlands"} <= countries)


def test_apply_plan_is_pure_data(dirty_csv, studio):
    """A plan is plain data: deriving then applying it is deterministic."""
    _, _, report = studio.clean(str(dirty_csv), dataset="customers")
    table, _ = studio.connect(str(dirty_csv))
    plan = derive_plan(report)
    cleaned_a, res_a = apply_plan(table, plan, dataset="x")
    cleaned_b, res_b = apply_plan(table, plan, dataset="x")
    assert cleaned_a.to_pylist() == cleaned_b.to_pylist()
    assert res_a.output_rows == res_b.output_rows


# --------------------------------------------------------------------------- #
# AI-ready export
# --------------------------------------------------------------------------- #
def test_ai_bundle_masks_pii_and_is_signed(studio, dirty_csv, tmp_path):
    result = studio.onboard(str(dirty_csv), dataset="customers",
                            out_dir=str(tmp_path / "out"), land=False)
    bundle = result.ai_bundle
    assert bundle is not None
    assert "email" in bundle.masked_fields

    corpus = Path(bundle.jsonl_path).read_text()
    # No raw PII anywhere in the AI corpus.
    for email in ("ada@example.com", "grace@example.com", "maggie@example.com"):
        assert email not in corpus
    # Documents are real JSON with text + metadata.
    first = json.loads(corpus.splitlines()[0])
    assert first["text"] and "metadata" in first

    # Manifest is signed + card written.
    manifest = json.loads(Path(bundle.manifest_path).read_text())
    assert manifest["signature"]
    assert Path(bundle.card_path).exists()


# --------------------------------------------------------------------------- #
# Full onboarding
# --------------------------------------------------------------------------- #
def test_onboard_writes_outputs_and_lands_governed_dataset(engine, studio, dirty_csv, tmp_path):
    result = studio.onboard(str(dirty_csv), dataset="customers", out_dir=str(tmp_path / "out"))

    # cleaned data exports exist and are readable
    parquet = Path(result.outputs["parquet"])
    assert parquet.exists()
    assert pq.read_table(parquet).num_rows == result.cleaning.output_rows
    assert Path(result.outputs["csv"]).exists()
    assert Path(result.outputs["report"]).exists()

    # landed as a governed dataset in the catalog, carrying PII tags + post-clean quality
    assert result.landed_dataset == "prepared/customers@1.0.0"
    meta = engine.catalog.get(DatasetRef(domain="prepared", name="customers", version="1.0.0"))
    assert meta is not None
    assert meta.row_count == result.cleaning.output_rows
    assert "email" in meta.schema_.pii_fields


# --------------------------------------------------------------------------- #
# Regression tests for the adversarial-review fixes
# --------------------------------------------------------------------------- #
import pyarrow as pa  # noqa: E402

from aegoria_core.dataprep.ai_export import _pii_fields_for  # noqa: E402
from aegoria_core.dataprep.models import AssessmentReport, CleaningPlan, CleaningStep  # noqa: E402
from aegoria_core.dataprep.profiler import assess as profile_assess  # noqa: E402


def test_pii_detection_fails_closed_without_governance():
    """Even with NO governance service, obvious PII must still be detected."""
    table = pa.table({
        "email": pa.array(["a@x.com", "b@x.com", "c@x.com"]),
        "city": pa.array(["paris", "rome", "oslo"]),
    })
    report = profile_assess(table, dataset="d", source="s", connector="file", governance=None)
    assert "email" in report.pii_columns  # heuristic fallback, not governance


def test_assessment_report_does_not_leak_raw_pii_values():
    table = pa.table({"email": pa.array(["secret@x.com", "secret@x.com", "other@x.com"])})
    report = profile_assess(table, dataset="d", source="s", connector="file", governance=None)
    col = next(c for c in report.columns if c.name == "email")
    assert col.pii and col.top_values == [] and col.numeric_min is None
    assert "secret@x.com" not in json.dumps(report.model_dump(), default=str)


def test_pii_fields_map_through_split_unit_rename():
    """A PII column renamed by split_unit (card -> card_value/_unit) stays masked."""
    report = AssessmentReport(source="s", connector="file", dataset="d", pii_columns=["card"])
    assert set(_pii_fields_for(report, ["card_value", "card_unit", "x"])) == {"card_value", "card_unit"}
    assert _pii_fields_for(report, ["card", "x"]) == ["card"]


def test_dedupe_keeps_null_distinct_from_empty_string():
    table = pa.table({"c": pa.array(["", None, "x"], pa.string())})
    cleaned, result = apply_plan(table, CleaningPlan(steps=[CleaningStep(op="dedupe_rows")]))
    assert result.output_rows == 3  # "" and None are NOT duplicates


def test_drop_all_columns_preserves_row_count():
    table = pa.table({"a": pa.nulls(2, pa.string()), "b": pa.nulls(2, pa.string())})
    cleaned, result = apply_plan(table, CleaningPlan(steps=[CleaningStep(op="drop_empty_columns")]))
    assert result.input_rows == 2 and result.output_rows == 2  # rows, not zeroed
    assert cleaned.num_columns == 0


def test_duplicate_column_names_do_not_crash_assess():
    table = pa.Table.from_arrays([pa.array(["a", "b"]), pa.array(["c", "d"])], names=["dup", "dup"])
    report = profile_assess(table, dataset="d", source="s", connector="file", governance=None)
    assert report.column_count == 2
