"""`aegoria` command-line interface (zero extra deps — stdlib argparse).

Thin wrapper over :class:`AegoriaEngine`. Subcommands are deliberately
domain-agnostic; richer authoring commands live in the ``aegoria-sdk`` package.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .config import AegoriaConfig
from .engine import CORE_VERSION, AegoriaEngine


def _engine(config_path: Optional[str]) -> AegoriaEngine:
    return AegoriaEngine.bootstrap(AegoriaConfig.load(config_path))


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_version(_: argparse.Namespace) -> int:
    _print({"core_version": CORE_VERSION})
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    engine = _engine(args.config)
    _print(engine.health())
    return 0


def cmd_packs(args: argparse.Namespace) -> int:
    engine = _engine(args.config)
    _print([
        {"id": m.id, "name": m.name, "version": m.version,
         "datasets": [d.name for d in m.datasets], "modalities": [x.value for x in m.modalities]}
        for m in engine.domain_packs.values()
    ])
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    engine = _engine(args.config)
    results = engine.catalog.search(args.query or "", domain=args.domain)
    _print([
        {"id": m.ref.id, "title": m.title, "modality": m.modality.value,
         "fair": round(m.fair.score, 2), "quality": round(m.quality_score, 2),
         "jurisdiction": m.jurisdiction.code, "rows": m.row_count}
        for m in results
    ])
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from .contracts.models import QuerySpec

    engine = _engine(args.config)
    spec = QuerySpec(sql=args.sql, purpose=args.purpose or "cli", epsilon=args.epsilon)
    result = engine.query(spec)
    _print({"columns": result.columns, "rows": result.rows[:50], "stats": result.stats.model_dump()})
    return 0


def cmd_assess(args: argparse.Namespace) -> int:
    from .dataprep import get_studio

    studio = get_studio(_engine(args.config))
    report = studio.assess(
        args.source, connector=args.connector, table=args.table,
        query=args.query, limit=args.limit, dataset=args.dataset,
    )
    _print(report.model_dump())
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Connect → assess → clean → write cleaned data, a JSON report and an AI bundle."""
    from .dataprep import get_studio

    studio = get_studio(_engine(args.config))
    result = studio.onboard(
        args.source, connector=args.connector, table=args.table, query=args.query,
        dataset=args.dataset, limit=args.limit, out_dir=args.out, domain=args.domain,
        land=not args.no_land, ai=not args.no_ai,
    )
    a, c = result.assessment, result.cleaning
    _print({
        "source": result.source,
        "connector": result.connector,
        "dataset": result.dataset,
        "rows": {"input": c.input_rows, "output": c.output_rows, "estimate": a.row_estimate,
                 "truncated": a.truncated},
        "quality": {"before": c.input_quality_score, "after": c.output_quality_score},
        "pii_columns": a.pii_columns,
        "duplicate_rows": a.duplicate_rows,
        "steps": [s.op for s in c.steps_applied],
        "issues": a.issues_summary,
        "landed_dataset": result.landed_dataset,
        "ai_bundle": result.ai_bundle.model_dump() if result.ai_bundle else None,
        "outputs": result.outputs,
    })
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegoria", description="Aegoria core engine CLI")
    p.add_argument("-c", "--config", default=None, help="path to aegoria.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="print core version").set_defaults(func=cmd_version)
    sub.add_parser("doctor", help="show engine health + wired providers").set_defaults(func=cmd_doctor)
    sub.add_parser("packs", help="list loaded domain-packs").set_defaults(func=cmd_packs)

    c = sub.add_parser("catalog", help="search the FAIR catalog")
    c.add_argument("query", nargs="?", default="")
    c.add_argument("--domain", default=None)
    c.set_defaults(func=cmd_catalog)

    q = sub.add_parser("query", help="run a governed, carbon-aware SQL query")
    q.add_argument("sql")
    q.add_argument("--purpose", default=None)
    q.add_argument("--epsilon", type=float, default=None, help="request differential privacy")
    q.set_defaults(func=cmd_query)

    def _source_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("source", help="path/URL of a database or file (csv/parquet/sqlite/postgres)")
        parser.add_argument("--connector", default=None, help="force a source connector (file|sqlite|sql)")
        parser.add_argument("--table", default=None, help="table/file to read when the source has many")
        parser.add_argument("--query", default=None, help="custom SQL to pull from the source")
        parser.add_argument("--dataset", default=None, help="name for the prepared dataset")

    a = sub.add_parser("assess", help="profile + quality/PII-assess an external source")
    _source_args(a)
    a.add_argument("--limit", type=int, default=50_000, help="rows to sample for assessment")
    a.set_defaults(func=cmd_assess)

    cl = sub.add_parser("clean", help="connect → assess → clean → cleaned data + report + AI bundle")
    _source_args(cl)
    cl.add_argument("--limit", type=int, default=200_000, help="max rows to clean")
    cl.add_argument("--out", default=None, help="output directory (default: <warehouse>/../exports/<dataset>)")
    cl.add_argument("--domain", default="prepared", help="domain to land the cleaned dataset under")
    cl.add_argument("--no-land", action="store_true", help="do not register the cleaned table in the lakehouse")
    cl.add_argument("--no-ai", action="store_true", help="do not emit the AI-ready JSONL bundle")
    cl.set_defaults(func=cmd_clean)
    return p


def app(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # surfaced cleanly to the shell
        print(f"aegoria: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(app())
