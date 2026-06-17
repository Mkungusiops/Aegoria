"""Aegoria SDK — author, validate and test domain-packs declaratively.

A *domain-pack* is how a brand-new market onboards onto Aegoria without anyone
touching the core engine. This SDK is the authoring toolchain around that pack:

    aegoria-pack new   <id>     # scaffold a fresh pack skeleton
    aegoria-pack validate <path>  # structural correctness of the manifest
    aegoria-pack lint     <path>  # validate + style/best-practice advisories
    aegoria-pack info     <path>  # human summary of what a pack declares

The same primitives are importable so a pack's own CI can gate merges:

    from aegoria_sdk import validate_manifest, scaffold_pack, PackTestHarness

Nothing here is market-specific and nothing here imports a concrete adapter or
service — the SDK speaks only the frozen ``aegoria_core`` contracts, exactly like
the engine does. That keeps the "core never changes" invariant intact: a pack is
data, and this is the toolkit for shaping that data correctly.
"""

from __future__ import annotations

from .scaffold import ScaffoldResult, scaffold_pack
from .testkit import HarnessResult, PackTestHarness, run_pack_quality_gates
from .validate import (
    Severity,
    ValidationIssue,
    ValidationReport,
    lint_manifest,
    validate_manifest,
    validate_path,
)

__version__ = "0.1.0"

__all__ = [
    # validation
    "validate_manifest",
    "validate_path",
    "lint_manifest",
    "ValidationReport",
    "ValidationIssue",
    "Severity",
    # scaffolding
    "scaffold_pack",
    "ScaffoldResult",
    # testkit
    "PackTestHarness",
    "HarnessResult",
    "run_pack_quality_gates",
    "__version__",
]
