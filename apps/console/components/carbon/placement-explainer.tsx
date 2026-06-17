import { ArrowRight, Ban, Check, MapPin, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import type { CarbonReading } from "@/lib/types";

/**
 * Carbon-aware placement walkthrough. Takes a representative query and shows
 * how the scheduler narrows candidate regions: residency fences eliminate
 * non-compliant regions first, then the lowest-carbon survivor wins. This is
 * the same logic the `carbon-aware` ComputeScheduler runs for every query.
 */
export function PlacementExplainer({ regions }: { regions: CarbonReading[] }) {
  const sorted = [...regions].sort((a, b) => a.gco2PerKwh - b.gco2PerKwh);
  // Demo query is EU-resident credit data: only EU-prefixed regions are eligible.
  const eligible = (r: CarbonReading) => r.region.startsWith("eu");
  const candidates = sorted.filter(eligible);
  const winner = candidates[0] ?? sorted[0];

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-hairline bg-veil/50 px-3 py-2.5">
        <div className="mb-1 text-[10px] uppercase tracking-wider text-faint">incoming query</div>
        <code className="block font-mono text-[11.5px] leading-snug text-auralis">
          SELECT AVG(income) FROM loan_applications WHERE decision=&apos;approved&apos;
        </code>
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10.5px] text-faint">
          <Badge tone="crimson">residency: EU</Badge>
          <Badge tone="pulse">differential privacy</Badge>
          <span>duckdb · aggregate</span>
        </div>
      </div>

      {/* Step rail */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-3">
        <div className="space-y-2">
          <StepLabel n={1} text="Candidate regions, greenest-first" />
          <div className="space-y-1.5">
            {sorted.map((r) => {
              const ok = eligible(r);
              return (
                <div
                  key={r.region}
                  className={
                    "flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 " +
                    (ok ? "border-hairline bg-veil-2/50" : "border-crimson/20 bg-crimson/[0.04] opacity-70")
                  }
                >
                  <div className="flex items-center gap-2">
                    {ok ? (
                      <Check size={12} className="text-verdant" />
                    ) : (
                      <Ban size={12} className="text-crimson" />
                    )}
                    <span className="font-mono text-[11px] text-lumen">{r.region}</span>
                  </div>
                  <span className="flex items-center gap-2">
                    <span className="tabular-nums text-[10.5px] text-muted">{r.gco2PerKwh}g</span>
                    {!ok && <span className="text-[9.5px] uppercase tracking-wide text-crimson/80">fenced</span>}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col items-center justify-center gap-1 px-1">
          <ArrowRight size={16} className="text-auralis/70" />
          <span className="whitespace-nowrap text-[9px] uppercase tracking-wider text-faint">filter + rank</span>
        </div>

        <div className="space-y-2">
          <StepLabel n={2} text="Residency-compliant, lowest carbon wins" />
          <div className="flex h-[calc(100%-1.75rem)] flex-col justify-center rounded-md border border-verdant/30 bg-verdant/5 p-3 text-center">
            <div className="flex items-center justify-center gap-2 text-verdant">
              <MapPin size={16} />
              <span className="font-display text-[18px] font-semibold text-lumen">{winner.region}</span>
            </div>
            <div className="mt-1 flex items-center justify-center gap-1.5 text-[11px] text-muted">
              <Sparkles size={12} className="text-verdant" />
              <span className="tabular-nums">{winner.gco2PerKwh} gCO₂/kWh</span>
              <span className="text-hairline">·</span>
              <span className="tabular-nums">{Math.round(winner.renewableFraction * 100)}% renewable</span>
            </div>
            <Badge tone="verdant" className="mx-auto mt-2.5" dot>
              placed here
            </Badge>
          </div>
        </div>
      </div>

      <p className="border-t border-hairline pt-3 text-[11px] leading-relaxed text-faint">
        Regions outside the EU are eliminated by the residency fence before carbon is even considered — compliance is a
        hard constraint, sustainability is the optimization within it. The same scheduler runs for every domain.
      </p>
    </div>
  );

  function StepLabel({ n, text }: { n: number; text: string }) {
    return (
      <div className="flex items-center gap-2">
        <span className="grid h-5 w-5 place-items-center rounded-full border border-auralis/40 bg-auralis/10 text-[10px] font-semibold text-auralis">
          {n}
        </span>
        <span className="text-[11px] font-medium text-muted">{text}</span>
      </div>
    );
  }
}
