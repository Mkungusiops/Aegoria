"""Scaffold a fresh domain-pack skeleton from a handful of inputs.

Onboarding a market starts here: ``scaffold_pack("climate-emissions")`` lays down
a directory that already validates, already has one dataset with a schema, a
quality rule, an ontology term, a semantic mapping, a connector, a default access
policy, and a matching CSV sample so ``aegoria-pack`` (and the pack's own CI) can
exercise the full path immediately.

The generated tree::

    <out>/<id>/
        manifest.yaml          # the declarative onboarding document
        sample_data/<ds>.csv   # rows that satisfy the starter schema + rules
        pack.py                # optional Python hooks (only with hooks=True)
        README.md              # pack-local quickstart

The skeleton is intentionally a *working* pack, not a stub: a new author edits
real, valid declarations rather than filling in blanks, and never sees a red
validator on a freshly scaffolded pack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Optional

import yaml

from aegoria_core.contracts.domain_pack import (
    AccessPolicySpec,
    ConnectorSpec,
    DatasetSpec,
    DomainPackManifest,
    OntologyTerm,
    SemanticMapping,
)
from aegoria_core.contracts.models import (
    FieldSchema,
    FieldType,
    License,
    Modality,
    QualityRule,
    Sensitivity,
    TableSchema,
)

_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class ScaffoldError(Exception):
    """Raised when scaffold inputs are invalid or the target already exists."""


@dataclass
class ScaffoldResult:
    """What ``scaffold_pack`` produced, for the CLI and for tests."""

    pack_id: str
    root: Path
    files: list[Path] = dc_field(default_factory=list)

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.yaml"


def _slug(value: str) -> str:
    """Lower-kebab a free-text name into a valid id fragment."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "dataset"


def _title(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _starter_dataset(dataset_name: str, modality: Modality) -> DatasetSpec:
    """A minimal-but-real dataset: an id, a name, a measured value, a timestamp.

    The schema is deliberately generic (no market meaning), mirroring how the core
    treats every dataset the same; meaning is attached later via semantic_mappings.
    """
    schema = TableSchema(
        name=dataset_name,
        version="1.0.0",
        modality=modality,
        fields=[
            FieldSchema(
                name="entity_id",
                type=FieldType.STRING,
                nullable=False,
                description="Stable identifier for the observed entity.",
                sensitivity=Sensitivity.INTERNAL,
            ),
            FieldSchema(
                name="observed_at",
                type=FieldType.TIMESTAMP,
                nullable=False,
                description="When the observation was recorded (UTC).",
                sensitivity=Sensitivity.INTERNAL,
            ),
            FieldSchema(
                name="metric",
                type=FieldType.STRING,
                nullable=False,
                description="Name of the measured quantity.",
                sensitivity=Sensitivity.INTERNAL,
            ),
            FieldSchema(
                name="value",
                type=FieldType.DOUBLE,
                nullable=False,
                description="Numeric measurement value.",
                unit="unit",
                sensitivity=Sensitivity.INTERNAL,
            ),
        ],
        primary_key=["entity_id", "observed_at", "metric"],
        partition_by=[],
        description=f"Starter dataset for the {dataset_name} domain.",
    )
    return DatasetSpec(
        name=dataset_name,
        title=_title(dataset_name),
        description=f"Auto-scaffolded starter dataset. Replace with the real {dataset_name} schema.",
        modality=modality,
        schema=schema,
        license=License(),
        quality_rules=[
            QualityRule(
                id=f"{dataset_name}-entity-not-null",
                field="entity_id",
                kind="not_null",
                severity="error",
                description="Every observation must identify its entity.",
            ),
            QualityRule(
                id=f"{dataset_name}-value-range",
                field="value",
                kind="range",
                params={"min": 0.0},
                severity="warn",
                description="Measured values are expected to be non-negative.",
            ),
        ],
        tags=["scaffold", "starter"],
        sample_data=f"sample_data/{dataset_name}.csv",
    )


def _build_manifest(
    *,
    pack_id: str,
    name: str,
    dataset_name: str,
    modality: Modality,
    maintainer: str,
    description: str,
) -> DomainPackManifest:
    ds = _starter_dataset(dataset_name, modality)
    term_id = f"{pack_id}:Observation"
    return DomainPackManifest(
        id=pack_id,
        name=name,
        version="0.1.0",
        description=description,
        maintainer=maintainer,
        license=License(),
        core_compat=">=0.1.0,<1.0.0",
        modalities=[modality],
        datasets=[ds],
        ontology=[
            OntologyTerm(
                id=term_id,
                label="Observation",
                description="A single measured observation in this domain.",
            )
        ],
        semantic_mappings=[
            SemanticMapping(dataset=dataset_name, field="value", term=term_id),
        ],
        connectors=[
            ConnectorSpec(
                id=f"{dataset_name}-csv",
                modality=modality,
                adapter="file",
                format="csv",
                options={"header": True},
                target_dataset=dataset_name,
            )
        ],
        access_policies=[
            AccessPolicySpec(
                id=f"{pack_id}-public-read",
                description="Default: allow public read access to non-PII fields.",
                effect="allow",
                roles=["public"],
                actions=["read", "query"],
                datasets=["*"],
            )
        ],
        metadata={"scaffolded_by": "aegoria-sdk"},
    )


def _manifest_to_yaml(manifest: DomainPackManifest) -> str:
    """Serialize a manifest to clean, by-alias YAML (``schema:`` not ``schema_:``)."""
    data = manifest.model_dump(by_alias=True, exclude_defaults=True, mode="json")
    header = (
        f"# Aegoria domain-pack manifest for {manifest.id!r}.\n"
        "# This file IS the onboarding: edit declarations, then run `aegoria-pack validate .`.\n"
        "# Docs: https://aegoria.dev/docs/domain-packs\n"
    )
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return header + body


def _sample_csv(dataset: DatasetSpec) -> str:
    """A few rows that satisfy the starter schema + quality rules."""
    header = ",".join(f.name for f in dataset.schema_.fields)
    rows = [
        "entity-001,2026-01-01T00:00:00Z,sample_metric,1.0",
        "entity-002,2026-01-01T01:00:00Z,sample_metric,2.5",
        "entity-003,2026-01-01T02:00:00Z,sample_metric,3.75",
    ]
    return header + "\n" + "\n".join(rows) + "\n"


def _pack_hooks_py(pack_id: str) -> str:
    """A pure-declarative pack needs no Python; this is an optional hook stub."""
    module = pack_id.replace("-", "_")
    return f'''"""Optional Python hooks for the {pack_id!r} domain-pack.

A pack is declarative first: ``manifest.yaml`` carries schemas, ontology, quality
rules and policy. You only need this file when a connector, model loader or custom
quality check requires real code. Hooks bind to the *same* adapter/service
protocols as the rest of the platform — they never reach into the core engine.

Register the pack so the engine can discover it via the ``aegoria.providers``
entry point (declared in this pack's ``pyproject.toml``)::

    [project.entry-points."aegoria.providers"]
    {module} = "{module}.pack:register"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aegoria_core.contracts.domain_pack import DomainPackManifest
from aegoria_core.registry import domain_pack

_MANIFEST = Path(__file__).with_name("manifest.yaml")


class {_class_name(pack_id)}Pack:
    """Runtime view of the pack: the manifest plus optional code hooks."""

    def __init__(self) -> None:
        self._manifest = DomainPackManifest.from_yaml(_MANIFEST)

    @property
    def manifest(self) -> DomainPackManifest:
        return self._manifest

    # Pure-declarative defaults — override only what your market needs.
    def connectors(self) -> dict[str, Any]:
        return {{}}

    def models(self) -> dict[str, Any]:
        return {{}}

    def custom_quality(self) -> dict[str, Any]:
        return {{}}


@domain_pack({pack_id!r})
def register() -> {_class_name(pack_id)}Pack:
    """Factory invoked by the registry when this pack's entry point loads."""
    return {_class_name(pack_id)}Pack()
'''


def _class_name(pack_id: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_]", pack_id) if part)


def _pack_readme(pack_id: str, name: str, dataset_name: str) -> str:
    return f"""# {name}

Aegoria domain-pack `{pack_id}`. This pack onboards the **{name}** market onto the
Aegoria lakehouse declaratively — no core-engine changes required.

## Layout

- `manifest.yaml` — the declarative onboarding document (schemas, ontology,
  quality rules, connectors, access policy). **This is the source of truth.**
- `sample_data/{dataset_name}.csv` — sample rows used to exercise the quality gate.
- `pack.py` *(optional)* — Python hooks for custom connectors / models.

## Develop

```bash
aegoria-pack validate .   # structural correctness
aegoria-pack lint .       # + best-practice advisories
aegoria-pack info .       # human summary
```

Wire the same checks into CI with `aegoria_sdk.testkit.PackTestHarness` to assert
sample data passes every quality gate before merge.
"""


def scaffold_pack(
    pack_id: str,
    *,
    out_dir: str | Path = ".",
    name: Optional[str] = None,
    dataset: Optional[str] = None,
    modality: Modality | str = Modality.STRUCTURED,
    maintainer: str = "",
    description: str = "",
    hooks: bool = False,
    force: bool = False,
) -> ScaffoldResult:
    """Generate a new, *already-valid* domain-pack skeleton under ``out_dir/<pack_id>``.

    Args:
        pack_id: lower-kebab id, e.g. ``"climate-emissions"`` (the directory name).
        out_dir: parent directory to create the pack in.
        name: human display name (defaults to a title-cased ``pack_id``).
        dataset: name of the seed dataset (defaults to a slug of ``name``).
        modality: data modality for the seed dataset.
        maintainer: maintainer string for the manifest.
        description: top-level pack description.
        hooks: also emit ``pack.py`` with registration + hook stubs.
        force: overwrite an existing manifest in the target directory.

    Returns:
        A :class:`ScaffoldResult` listing the created files.

    Raises:
        ScaffoldError: invalid id, or the pack already exists and ``force`` is off.
    """
    if not _ID_RE.match(pack_id):
        raise ScaffoldError(
            f"invalid pack id {pack_id!r}: use lower-case letters, digits and hyphens, "
            "starting with a letter (e.g. 'climate-emissions')"
        )

    modality = Modality(modality) if not isinstance(modality, Modality) else modality
    name = name or _title(pack_id)
    dataset_name = _slug(dataset) if dataset else _slug(pack_id) + "-records"
    description = description or f"Aegoria domain-pack for the {name} market."

    root = Path(out_dir) / pack_id
    manifest_path = root / "manifest.yaml"
    if manifest_path.exists() and not force:
        raise ScaffoldError(
            f"refusing to overwrite existing pack at {manifest_path} (pass force=True to replace)"
        )

    manifest = _build_manifest(
        pack_id=pack_id,
        name=name,
        dataset_name=dataset_name,
        modality=modality,
        maintainer=maintainer,
        description=description,
    )
    ds = manifest.datasets[0]

    # Create the tree.
    sample_dir = root / "sample_data"
    sample_dir.mkdir(parents=True, exist_ok=True)

    result = ScaffoldResult(pack_id=pack_id, root=root)

    manifest_path.write_text(_manifest_to_yaml(manifest))
    result.files.append(manifest_path)

    sample_path = sample_dir / f"{dataset_name}.csv"
    sample_path.write_text(_sample_csv(ds))
    result.files.append(sample_path)

    readme_path = root / "README.md"
    readme_path.write_text(_pack_readme(pack_id, name, dataset_name))
    result.files.append(readme_path)

    if hooks:
        pack_py = root / "pack.py"
        pack_py.write_text(_pack_hooks_py(pack_id))
        result.files.append(pack_py)

    return result
