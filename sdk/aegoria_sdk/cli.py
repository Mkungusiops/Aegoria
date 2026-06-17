"""``aegoria-pack`` — the command-line entry point for authoring domain-packs.

Subcommands:

    aegoria-pack new <id> [--name ...] [--dataset ...] [--modality ...]
                          [--out DIR] [--hooks] [--force]
        Scaffold a new, already-valid pack skeleton.

    aegoria-pack validate <path> [--strict]
        Hard structural checks. Exit 0 if no errors. ``--strict`` also fails on warnings.

    aegoria-pack lint <path> [--strict]
        Structural checks + best-practice advisories.

    aegoria-pack info <path>
        Human-readable summary of what a pack declares.

``<path>`` may be a pack directory or a ``manifest.yaml`` file. All commands print
human output by default and accept ``--json`` for machine consumption (so the same
binary serves both a developer and a CI step).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from aegoria_core.contracts.domain_pack import DomainPackManifest

from . import __version__
from .scaffold import ScaffoldError, scaffold_pack
from .validate import validate_path


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _resolve_manifest_path(path: str) -> Path:
    p = Path(path)
    return p / "manifest.yaml" if p.is_dir() else p


def _emit(obj: object, *, as_json: bool, render: str) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(render)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_new(args: argparse.Namespace) -> int:
    try:
        result = scaffold_pack(
            args.id,
            out_dir=args.out,
            name=args.name,
            dataset=args.dataset,
            modality=args.modality,
            maintainer=args.maintainer,
            description=args.description or "",
            hooks=args.hooks,
            force=args.force,
        )
    except ScaffoldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    files = [str(f) for f in result.files]
    render = "\n".join(
        [
            f"Scaffolded domain-pack {result.pack_id!r} at {result.root}",
            *(f"  + {f}" for f in files),
            "",
            "Next:",
            f"  aegoria-pack validate {result.root}",
            f"  aegoria-pack info {result.root}",
        ]
    )
    _emit(
        {"pack_id": result.pack_id, "root": str(result.root), "files": files},
        as_json=args.json,
        render=render,
    )
    return 0


def _run_checks(args: argparse.Namespace, *, lint: bool) -> int:
    report = validate_path(_resolve_manifest_path(args.path), lint=lint)
    payload = report.model_dump(mode="json")
    _emit(payload, as_json=args.json, render=report.render())

    if not report.ok:
        return 1
    if args.strict and report.warnings:
        if not args.json:
            print("\nstrict mode: warnings present, failing.", file=sys.stderr)
        return 1
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    return _run_checks(args, lint=False)


def cmd_lint(args: argparse.Namespace) -> int:
    return _run_checks(args, lint=True)


def cmd_info(args: argparse.Namespace) -> int:
    manifest_path = _resolve_manifest_path(args.path)
    try:
        manifest = DomainPackManifest.from_yaml(manifest_path)
    except FileNotFoundError:
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    except Exception as exc:  # malformed manifest — point the user at `validate`
        print(f"error: could not load manifest: {exc}", file=sys.stderr)
        print("hint: run `aegoria-pack validate` for details.", file=sys.stderr)
        return 2

    summary = _summarize(manifest)
    _emit(summary, as_json=args.json, render=_render_info(manifest, summary))
    return 0


def _summarize(manifest: DomainPackManifest) -> dict[str, object]:
    pii_fields = sum(len(ds.schema_.pii_fields) for ds in manifest.datasets)
    quality_rules = sum(len(ds.quality_rules) for ds in manifest.datasets)
    return {
        "id": manifest.id,
        "name": manifest.name,
        "version": manifest.version,
        "core_compat": manifest.core_compat,
        "maintainer": manifest.maintainer,
        "modalities": [m.value for m in manifest.modalities],
        "datasets": [
            {
                "name": ds.name,
                "modality": ds.modality.value,
                "fields": len(ds.schema_.fields),
                "pii_fields": ds.schema_.pii_fields,
                "quality_rules": len(ds.quality_rules),
                "sample_data": ds.sample_data,
            }
            for ds in manifest.datasets
        ],
        "counts": {
            "datasets": len(manifest.datasets),
            "ontology_terms": len(manifest.ontology),
            "semantic_mappings": len(manifest.semantic_mappings),
            "connectors": len(manifest.connectors),
            "models": len(manifest.models),
            "access_policies": len(manifest.access_policies),
            "pii_fields": pii_fields,
            "quality_rules": quality_rules,
        },
    }


def _render_info(manifest: DomainPackManifest, summary: dict[str, object]) -> str:
    counts = summary["counts"]  # type: ignore[index]
    lines = [
        f"{manifest.name}  ({manifest.id} v{manifest.version})",
        f"  {manifest.description}" if manifest.description else "",
        f"  core-compat : {manifest.core_compat}",
        f"  maintainer  : {manifest.maintainer or '-'}",
        f"  modalities  : {', '.join(m.value for m in manifest.modalities) or '-'}",
        "",
        "  Counts:",
        f"    datasets ........... {counts['datasets']}",  # type: ignore[index]
        f"    ontology terms ..... {counts['ontology_terms']}",  # type: ignore[index]
        f"    semantic mappings .. {counts['semantic_mappings']}",  # type: ignore[index]
        f"    connectors ......... {counts['connectors']}",  # type: ignore[index]
        f"    models ............. {counts['models']}",  # type: ignore[index]
        f"    access policies .... {counts['access_policies']}",  # type: ignore[index]
        f"    quality rules ...... {counts['quality_rules']}",  # type: ignore[index]
        f"    PII fields ......... {counts['pii_fields']}",  # type: ignore[index]
        "",
        "  Datasets:",
    ]
    for ds in manifest.datasets:
        pii = f" pii={ds.schema_.pii_fields}" if ds.schema_.pii_fields else ""
        sample = " sample" if ds.sample_data else ""
        lines.append(
            f"    - {ds.name} [{ds.modality.value}] "
            f"{len(ds.schema_.fields)} field(s), {len(ds.quality_rules)} rule(s){pii}{sample}"
        )
    return "\n".join(line for line in lines if line != "")


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegoria-pack",
        description="Author, validate and inspect Aegoria domain-packs.",
    )
    parser.add_argument("--version", action="version", version=f"aegoria-pack {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = sub.add_parser("new", help="scaffold a new domain-pack skeleton")
    p_new.add_argument("id", help="pack id, lower-kebab (e.g. climate-emissions)")
    p_new.add_argument("--out", default=".", help="parent directory for the new pack (default: .)")
    p_new.add_argument("--name", default=None, help="human display name")
    p_new.add_argument("--dataset", default=None, help="name of the seed dataset")
    p_new.add_argument(
        "--modality", default="structured",
        help="seed dataset modality (structured, time_series, geospatial, imagery, ...)",
    )
    p_new.add_argument("--maintainer", default="", help="maintainer string for the manifest")
    p_new.add_argument("--description", default=None, help="top-level pack description")
    p_new.add_argument("--hooks", action="store_true", help="also emit pack.py with hook stubs")
    p_new.add_argument("--force", action="store_true", help="overwrite an existing pack")
    p_new.add_argument("--json", action="store_true", help="emit JSON")
    p_new.set_defaults(func=cmd_new)

    # validate
    p_val = sub.add_parser("validate", help="run structural checks on a pack manifest")
    p_val.add_argument("path", help="pack directory or manifest.yaml path")
    p_val.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p_val.add_argument("--json", action="store_true", help="emit JSON")
    p_val.set_defaults(func=cmd_validate)

    # lint
    p_lint = sub.add_parser("lint", help="structural checks + best-practice advisories")
    p_lint.add_argument("path", help="pack directory or manifest.yaml path")
    p_lint.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p_lint.add_argument("--json", action="store_true", help="emit JSON")
    p_lint.set_defaults(func=cmd_lint)

    # info
    p_info = sub.add_parser("info", help="summarize what a pack declares")
    p_info.add_argument("path", help="pack directory or manifest.yaml path")
    p_info.add_argument("--json", action="store_true", help="emit JSON")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
