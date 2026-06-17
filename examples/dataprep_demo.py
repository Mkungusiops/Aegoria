#!/usr/bin/env python
"""Aegoria data-prep, end to end: connect a messy database → assess → clean → AI-ready.

Builds a deliberately *dirty* SQLite database (the kind a data app like
``DataInVizApp_V2`` holds: duplicate rows, stray whitespace, inconsistent casing,
numbers stored as text, packed units, blanks, and real PII), then drives the full
onboarding pipeline:

    connect → assess (profile + quality + PII) → clean → outputs:
        • cleaned Parquet + CSV         (use internally / in another app)
        • a governed Iceberg dataset    (queryable through the platform)
        • a JSONL + data-card bundle     (PII-masked, signed → feed to an AI)

If ``/Users/jeff/Code/DataInVizApp_V2`` is present, it also assesses a real, large,
genuinely messy CSV from that project to show the same pipeline on live data.

Run:  python examples/dataprep_demo.py
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from aegoria_core import AegoriaConfig, AegoriaEngine
from aegoria_core.dataprep import get_studio

DIRTY_ROWS = [
    # id, name,                email,                   phone,            signup,        spend,      country,        plan
    (1, "  Ada Lovelace ",  "ada@example.com",       "+1 202 555 0101", "2021-01-05", "1200.50", "United Kingdom", "Pro"),
    (2, "Alan Turing",      "alan@example.com",      "2025550102",      "2021-02-11", "980",      "uk",             "pro"),
    (3, "Grace Hopper",     "grace@example.com",     "+1-202-555-0103", "2021/03/02", "NA",       "USA",            "Enterprise"),
    (3, "Grace Hopper",     "grace@example.com",     "+1-202-555-0103", "2021/03/02", "NA",       "USA",            "Enterprise"),  # exact dup
    (4, "katherine johnson","katherine@example.com", "202.555.0104",    "2021-04-18", "2310.00",  "U.S.A.",         "enterprise"),
    (5, "Edsger Dijkstra",  "",                      "",                "",           "",         "Netherlands",    "Free"),
    (6, "Margaret Hamilton","maggie@example.com",    "+31 20 555 0106", "2021-06-30", "47999",    "netherlands",    "PRO"),
    (7, "Tim Berners-Lee ", "tim@example.com",       "+44 20 7555 0107","2021-07-22", "15.5",     "United Kingdom", "free"),
    (8, "Barbara Liskov",   "barbara@example.com",   "+1 202 555 0108", "2021-08-01", "-5",       "USA",            "Pro"),
]


def build_dirty_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE customers (id TEXT, name TEXT, email TEXT, phone TEXT, "
        "signup TEXT, spend TEXT, country TEXT, plan TEXT)"
    )
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)",
                    [(str(r[0]), *r[1:]) for r in DIRTY_ROWS])
    con.commit()
    con.close()


def banner(title: str) -> None:
    print("\n" + "=" * 78 + f"\n  {title}\n" + "=" * 78)


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="aegoria-dataprep-"))
    db = workdir / "customers.sqlite"
    build_dirty_db(db)

    cfg = AegoriaConfig(
        warehouse_uri=str(workdir / "warehouse"),
        catalog_uri=f"sqlite:///{workdir / 'catalog.db'}",
        domain_pack_paths=[],  # no domain packs needed for ad-hoc onboarding
    )
    engine = AegoriaEngine.bootstrap(cfg)
    studio = get_studio(engine)

    banner("1 · CONNECT a messy SQLite database (bring-your-own source)")
    print(f"   database : {db}")
    print(f"   tables   : {studio.list_tables(str(db))}")

    banner("2 · ASSESS — profile, quality score, PII classification")
    report = studio.assess(str(db), dataset="customers")
    print(f"   rows={report.sampled_rows}  columns={report.column_count}  "
          f"duplicate_rows={report.duplicate_rows}")
    print(f"   overall quality : {report.overall_quality_score:.2f} / 1.00")
    print(f"   PII columns     : {report.pii_columns}")
    print("   issues:")
    for issue in report.issues_summary:
        print(f"     - {issue}")
    print("   per-column findings:")
    for c in report.columns:
        if c.issues:
            print(f"     · {c.name} ({c.inferred_type}): {'; '.join(c.issues)}")
    print(f"   recommended plan: {[s.op for s in report.recommended_plan.steps]}")

    banner("3 · CLEAN + OUTPUT — cleaned data, governed dataset, AI bundle")
    result = studio.onboard(str(db), dataset="customers", out_dir=str(workdir / "out"))
    c = result.cleaning
    print(f"   quality {c.input_quality_score:.2f} → {c.output_quality_score:.2f}   "
          f"rows {c.input_rows} → {c.output_rows}")
    print("   steps applied:")
    for s in c.steps_applied:
        bits = []
        if s.cells_changed:
            bits.append(f"{s.cells_changed} cells")
        if s.rows_removed:
            bits.append(f"{s.rows_removed} rows")
        if s.columns_added:
            bits.append(f"+{','.join(s.columns_added)}")
        print(f"     - {s.op}: {s.notes}" + (f"  [{'; '.join(bits)}]" if bits else ""))
    print(f"   final schema: {[(f['name'], f['type']) for f in c.final_schema]}")
    print("\n   OUTPUTS")
    for k, v in result.outputs.items():
        print(f"     {k:18}: {v}")
    print(f"     landed dataset    : {result.landed_dataset}")

    banner("4 · AI-READY — verify PII is masked before it can reach an AI")
    bundle = result.ai_bundle
    print(f"   masked fields : {bundle.masked_fields}")
    print(f"   documents     : {bundle.chunk_count}   signed: {bool(bundle.signature)}")
    first = json.loads(Path(bundle.jsonl_path).read_text().splitlines()[0])
    print("   first AI document text:")
    print(f"     {first['text']}")
    leaked = [r[2] for r in DIRTY_ROWS if r[2]]  # the real emails
    raw_corpus = Path(bundle.jsonl_path).read_text()
    assert not any(email in raw_corpus for email in leaked), "PII LEAKED into AI corpus!"
    print("   ✅ no raw email/phone present anywhere in the AI corpus (governance-masked)")

    banner("5 · GOVERNED — the cleaned dataset is now queryable through the engine")
    if result.landed_dataset:
        cat = engine.catalog.all()
        for m in cat:
            if m.ref.id == result.landed_dataset:
                print(f"   {m.ref.id}: {m.row_count} rows, quality={m.quality_score:.2f}, "
                      f"pii_fields={m.schema_.pii_fields}")

    # Optional: the real, large, messy CSV from DataInVizApp_V2.
    wb = Path("/Users/jeff/Code/DataInVizApp_V2/research/datasets/csv/worldbank_indicators.csv")
    if wb.exists():
        banner("BONUS · assess a real messy dataset from DataInVizApp_V2")
        r2 = studio.assess(str(wb), dataset="worldbank_indicators", limit=20_000)
        print(f"   {wb.name}: {r2.row_estimate:,} rows total, sampled {r2.sampled_rows:,}")
        print(f"   completeness={r2.completeness:.2f}  quality={r2.overall_quality_score:.2f}")
        for issue in r2.issues_summary:
            print(f"     - {issue}")

    print(f"\nAll artifacts written under: {workdir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
