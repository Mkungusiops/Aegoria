"""Declarative engine configuration — selects providers without touching code.

The same engine becomes a laptop lakehouse or a multi-cloud mesh purely by
changing which adapters/services this config selects. Privacy and sovereignty
are defaults here, not add-ons: differential privacy and residency are on unless
a config explicitly relaxes them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from .errors import ConfigError


class ProviderSelection(BaseModel):
    """Which provider implements each capability, plus its construction options."""

    name: str
    options: dict[str, Any] = Field(default_factory=dict)


class PrivacyDefaults(BaseModel):
    differential_privacy: bool = True       # ON by default
    default_epsilon: float = 1.0
    default_delta: float = 1e-6
    pii_auto_classify: bool = True
    deny_export_of_pii: bool = True
    residency_enforced: bool = True


class CarbonConfig(BaseModel):
    source: str = "static"                   # CarbonSource adapter name
    # region -> gCO2/kWh for the `static` source; live sources override.
    intensities: dict[str, float] = Field(
        default_factory=lambda: {"local": 380.0, "eu-north": 28.0, "us-west": 210.0, "ap-south": 640.0}
    )
    optimize: bool = True                    # carbon-aware placement enabled


class AegoriaConfig(BaseModel):
    deployment: str = "lite"                 # lite | scaleout | edge
    warehouse_uri: str = "./.aegoria/warehouse"
    catalog_uri: str = "sqlite:///./.aegoria/catalog.db"
    default_jurisdiction: str = "GLOBAL"
    domain_pack_paths: list[str] = Field(default_factory=lambda: ["./domain-packs"])
    domain_packs: list[str] = Field(default_factory=list)  # explicit ids to load (else all discovered)

    adapters: dict[str, ProviderSelection] = Field(
        default_factory=lambda: {
            "storage": ProviderSelection(name="local-fs"),
            "catalog": ProviderSelection(name="sql"),
            "compute": ProviderSelection(name="duckdb"),
            "stream": ProviderSelection(name="inproc"),
            "identity": ProviderSelection(name="static"),
            "provenance": ProviderSelection(name="ed25519"),
            "carbon": ProviderSelection(name="static"),
        }
    )
    services: dict[str, str] = Field(
        default_factory=lambda: {
            "lakehouse": "iceberg",
            "ingestion": "default",
            "catalog": "default",
            "governance": "default",
            "scheduler": "carbon-aware",
            "knowledge_graph": "default",
            "ml": "default",
            "provenance": "default",
        }
    )
    privacy: PrivacyDefaults = Field(default_factory=PrivacyDefaults)
    carbon: CarbonConfig = Field(default_factory=CarbonConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, path: Optional[str | Path] = None) -> "AegoriaConfig":
        """Load from YAML (falls back to AEGORIA_CONFIG env, then sane lite defaults)."""
        path = path or os.environ.get("AEGORIA_CONFIG")
        if not path:
            default = Path("aegoria.yaml")
            path = default if default.exists() else None
        if path is None:
            return cls()
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"config file not found: {p}")
        return cls.model_validate(yaml.safe_load(p.read_text()) or {})

    def warehouse_path(self) -> Path:
        return Path(self.warehouse_uri)
