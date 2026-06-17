"""``static`` carbon source — fixed grid-intensity table for the lite engine.

Reads ``config.carbon.intensities`` (region -> gCO2/kWh) and reports them as
:class:`CarbonReading` values. Live sources (ElectricityMaps, WattTime) implement
the same :class:`~aegoria_core.contracts.adapters.CarbonSource` contract; the
carbon-aware scheduler treats them identically.
"""

from __future__ import annotations

from typing import Any

import structlog

from ..config import AegoriaConfig
from ..contracts.models import CarbonReading
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.carbon.static")

# Coarse renewable-fraction guesses for readability; lower intensity ~ greener.
def _renewable_fraction(gco2_per_kwh: float) -> float:
    # Map 0 gCO2 -> ~1.0 renewable, 800 gCO2 -> ~0.0, clamped.
    frac = 1.0 - (gco2_per_kwh / 800.0)
    return max(0.0, min(1.0, round(frac, 3)))


class StaticCarbonSource:
    """Serves grid carbon intensity from a fixed per-region table."""

    name = "static"

    def __init__(self, intensities: dict[str, float]) -> None:
        self._intensities = dict(intensities) or {"local": 380.0}

    # -- CarbonSource --------------------------------------------------- #
    def intensity(self, region: str) -> CarbonReading:
        gco2 = self._intensities.get(region)
        if gco2 is None:
            # Unknown region: fall back to a conservative high intensity.
            gco2 = max(self._intensities.values()) if self._intensities else 500.0
        return CarbonReading(
            region=region,
            gco2_per_kwh=float(gco2),
            renewable_fraction=_renewable_fraction(float(gco2)),
            source="static",
        )

    def regions(self) -> list[str]:
        return sorted(self._intensities)


@adapter("carbon", "static")
def make_static_carbon(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> StaticCarbonSource:
    """Factory the engine invokes to build the static carbon source."""
    return StaticCarbonSource(config.carbon.intensities)
