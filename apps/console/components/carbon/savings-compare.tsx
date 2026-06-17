import { TrendingDown } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import { HEX } from "./intensity";

/**
 * Carbon savings vs a naive baseline. The naive scheduler pins compute to the
 * caller's local region; the carbon-aware scheduler relocates eligible work to
 * the greenest compliant region. This renders the two as proportional bars and
 * the percentage avoided.
 */
export function SavingsCompare({
  awareG,
  naiveG,
}: {
  awareG: number; // gCO₂ per query with carbon-aware placement
  naiveG: number; // gCO₂ per query pinned to the local (caller) region
}) {
  const max = Math.max(awareG, naiveG, 0.0001);
  const savedPct = naiveG > 0 ? Math.round(((naiveG - awareG) / naiveG) * 100) : 0;

  const Row = ({ label, value, color, hint }: { label: string; value: number; color: string; hint: string }) => (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11.5px]">
        <span className="text-muted">{label}</span>
        <span className="tabular-nums text-lumen">
          {value.toFixed(2)} <span className="text-faint">gCO₂/query</span>
        </span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-veil-3">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${(value / max) * 100}%`, background: color }}
        />
      </div>
      <div className="mt-0.5 text-[10px] text-faint">{hint}</div>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-md border border-verdant/30 bg-verdant/5 px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-md border border-verdant/30 bg-veil-2 text-verdant">
            <TrendingDown size={16} />
          </span>
          <div className="leading-tight">
            <div className="text-[12.5px] font-medium text-lumen">Carbon avoided per query</div>
            <div className="text-[10.5px] text-faint">carbon-aware vs naive same-region baseline</div>
          </div>
        </div>
        <Badge tone="verdant">−{savedPct}%</Badge>
      </div>

      <div className="space-y-3">
        <Row
          label="Naive — pinned to local region"
          value={naiveG}
          color={HEX.crimson}
          hint="compute runs wherever the caller sits, regardless of grid mix"
        />
        <Row
          label="Carbon-aware placement"
          value={awareG}
          color={HEX.verdant}
          hint="relocated to greenest residency-compliant region"
        />
      </div>

      <div className="grid grid-cols-3 gap-3 border-t border-hairline pt-3 text-center">
        <Metric value={`${savedPct}%`} label="less carbon" tone="text-verdant" />
        <Metric value={`${(naiveG - awareG).toFixed(2)}g`} label="saved / query" tone="text-lumen" />
        <Metric value={`${(((naiveG - awareG) * 18420) / 1000).toFixed(1)}kg`} label="saved / day" tone="text-verdant" />
      </div>
    </div>
  );
}

function Metric({ value, label, tone }: { value: string; label: string; tone: string }) {
  return (
    <div>
      <div className={`font-display text-[18px] font-semibold tabular-nums ${tone}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-faint">{label}</div>
    </div>
  );
}
