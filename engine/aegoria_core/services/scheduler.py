"""``carbon-aware`` compute scheduler — greenest-capable placement + execution.

Placement: among the compute adapter's capable regions, pick the one with the
LOWEST grid carbon intensity (from the carbon adapter). Execution: run on that
placement via the compute adapter, then hand the Arrow result to governance so
mask / aggregate_only / differential_privacy obligations are enforced BEFORE the
rows are materialized. Energy is estimated from bytes scanned and converted to
grams of CO2 via the chosen region's intensity, and DP spend is recorded in the
returned :class:`QueryStats`.
"""

from __future__ import annotations

from typing import Any, Optional

import structlog

from ..contracts.models import (
    CarbonReading,
    Obligation,
    QueryResult,
    QuerySpec,
)
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.scheduler")

# Heuristic: energy per byte scanned (kWh/byte). ~0.2 kWh per GiB scanned.
_KWH_PER_BYTE = 0.2 / (1024 ** 3)


class CarbonAwareScheduler:
    """Places compute on the greenest capable region, runs, then enforces obligations."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx

    @property
    def _compute(self) -> Any:
        return self._ctx.adapter("compute")

    @property
    def _carbon(self) -> Any:
        return self._ctx.adapter("carbon")

    # -- ComputeScheduler ----------------------------------------------- #
    def place(self, spec: QuerySpec, table_paths: dict[str, str]) -> dict[str, Any]:
        compute = self._compute
        candidate_regions = list(compute.regions) or ["local"]
        est = compute.estimate(spec, table_paths)
        energy_kwh = max(est.bytes_scanned, 1) * _KWH_PER_BYTE

        best_region = None
        best_intensity = None
        for region in candidate_regions:
            reading = self._carbon.intensity(region)
            if best_intensity is None or reading.gco2_per_kwh < best_intensity:
                best_intensity = reading.gco2_per_kwh
                best_region = region
        best_region = best_region or "local"
        best_intensity = best_intensity if best_intensity is not None else 380.0
        estimated_carbon_g = energy_kwh * best_intensity

        return {
            "engine": compute.name,
            "region": best_region,
            "estimated_carbon_g": round(estimated_carbon_g, 6),
            "reason": (
                f"lowest grid intensity {best_intensity:.0f} gCO2/kWh among "
                f"{candidate_regions}"
            ),
        }

    def execute(
        self,
        spec: QuerySpec,
        table_paths: dict[str, str],
        obligations: Optional[list[Obligation]] = None,
    ) -> QueryResult:
        obligations = obligations or []
        placement = self.place(spec, table_paths)
        region = placement["region"]

        table, stats = self._compute.execute(spec, table_paths)
        stats.region = region

        # Privacy gate: a non-owner may not project raw PII columns at row level.
        # A `mask` obligation carries the PII field set governance decided to protect;
        # if any of those columns surface in the query output, this is a raw-PII pull
        # (an aggregate's output would expose no PII column) — deny it.
        mask = next((o for o in (obligations or []) if o.kind == "mask"), None)
        if mask:
            leaked = sorted(set(mask.params.get("fields", [])) & set(table.column_names))
            if leaked:
                from ..errors import AccessDenied

                raise AccessDenied(
                    f"raw projection of PII column(s) {leaked} is not permitted; "
                    "aggregate the data or request a de-identified view"
                )

        # Enforce access obligations on the result BEFORE materializing rows.
        governance = self._ctx.service("governance")
        schema = self._result_schema(table)
        dp = next((o for o in obligations if o.kind == "differential_privacy"), None)
        table = governance.apply_obligations(table, obligations, schema=schema)

        # Energy + carbon from the chosen region's live intensity.
        reading = self._carbon.intensity(region)
        energy_kwh = max(stats.bytes_scanned, 1) * _KWH_PER_BYTE
        stats.energy_kwh = round(energy_kwh, 9)
        stats.carbon_g = round(energy_kwh * reading.gco2_per_kwh, 9)
        stats.rows = table.num_rows
        if dp is not None:
            epsilon = float(dp.params.get("epsilon", self._ctx.config.privacy.default_epsilon))
            stats.dp_applied = True
            stats.epsilon_spent = epsilon
            # Record budget spend against the requesting purpose's datasets.
            if hasattr(governance, "spend_budget"):
                subject = spec.purpose or "query"
                for ds in spec.datasets:
                    governance.spend_budget(subject, ds, epsilon)

        result = QueryResult(
            columns=table.column_names,
            rows=table.to_pylist(),
            stats=stats,
        )
        log.info(
            "execute",
            engine=stats.engine,
            region=region,
            rows=stats.rows,
            carbon_g=stats.carbon_g,
            dp=stats.dp_applied,
        )
        return result

    def carbon_snapshot(self) -> list[CarbonReading]:
        return [self._carbon.intensity(r) for r in self._carbon.regions()]

    # -- helpers -------------------------------------------------------- #
    @staticmethod
    def _result_schema(table: Any) -> Any:
        """Build a minimal TableSchema describing the result columns for masking."""
        from ..contracts.models import FieldSchema, FieldType, TableSchema

        type_map = {
            "string": FieldType.STRING,
            "int64": FieldType.LONG,
            "int32": FieldType.INT,
            "double": FieldType.DOUBLE,
            "float": FieldType.FLOAT,
            "bool": FieldType.BOOL,
        }
        fields = []
        for name in table.column_names:
            arrow_type = str(table.schema.field(name).type)
            fields.append(FieldSchema(name=name, type=type_map.get(arrow_type, FieldType.STRING)))
        return TableSchema(name="_result", fields=fields)


@service("scheduler", "carbon-aware")
def make_carbon_aware_scheduler(*, ctx: EngineContext) -> CarbonAwareScheduler:
    """Factory the engine invokes to build the carbon-aware scheduler service."""
    return CarbonAwareScheduler(ctx)
