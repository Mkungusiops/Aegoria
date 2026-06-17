import { Leaf, Zap } from "lucide-react";
import { ProgressBar, Badge } from "@/components/ui/primitives";
import type { CarbonReading } from "@/lib/types";
import { intensityTone, intensityLabel } from "./intensity";

/**
 * Region carbon table, greenest-first. Each row shows live grid intensity
 * (gCO₂/kWh), a renewable-fraction bar, and a chip marking the region the
 * scheduler would currently pick. The carbon-aware scheduler always prefers
 * the lowest-intensity region that satisfies residency + capability.
 */
export function RegionTable({ regions }: { regions: CarbonReading[] }) {
  const sorted = [...regions].sort((a, b) => a.gco2PerKwh - b.gco2PerKwh);
  const greenest = sorted[0]?.region;
  const max = Math.max(...sorted.map((r) => r.gco2PerKwh), 1);

  return (
    <div className="space-y-2">
      {sorted.map((r, i) => {
        const tone = intensityTone(r.gco2PerKwh);
        const isGreenest = r.region === greenest;
        return (
          <div
            key={r.region}
            className={
              "rounded-md border px-3 py-2.5 transition-colors " +
              (isGreenest ? "border-verdant/30 bg-verdant/5" : "border-hairline bg-veil-2/40")
            }
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="grid h-6 w-6 place-items-center rounded-md bg-veil-3 font-mono text-[11px] tabular-nums text-faint">
                  {i + 1}
                </span>
                <div className="leading-tight">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[12.5px] text-lumen">{r.region}</span>
                    {isGreenest && (
                      <Badge tone="verdant" dot>
                        scheduler pick
                      </Badge>
                    )}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-faint">{intensityLabel(r.gco2PerKwh)} intensity</div>
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-baseline gap-1">
                  <span className="font-display text-[16px] font-semibold tabular-nums text-lumen">{r.gco2PerKwh}</span>
                  <span className="text-[10px] text-faint">gCO₂/kWh</span>
                </div>
              </div>
            </div>

            <div className="mt-2.5 grid grid-cols-[1fr_auto] items-center gap-3">
              <div>
                <div className="mb-1 flex items-center justify-between text-[10px] text-faint">
                  <span className="flex items-center gap-1">
                    <Leaf size={10} className="text-verdant" /> renewable
                  </span>
                  <span className="tabular-nums text-muted">{Math.round(r.renewableFraction * 100)}%</span>
                </div>
                <ProgressBar value={r.renewableFraction * 100} tone="verdant" />
              </div>
              <div className="w-24">
                <div className="mb-1 flex items-center justify-between text-[10px] text-faint">
                  <span className="flex items-center gap-1">
                    <Zap size={10} className={tone === "crimson" ? "text-crimson" : "text-solar"} /> carbon
                  </span>
                </div>
                <ProgressBar value={(r.gco2PerKwh / max) * 100} tone={tone} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
