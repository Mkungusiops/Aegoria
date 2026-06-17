import { cn } from "@/lib/cn";
import type { FairFlags } from "@/lib/types";

const FAIR_AXES: { key: keyof FairFlags; letter: string; label: string }[] = [
  { key: "findable", letter: "F", label: "Findable" },
  { key: "accessible", letter: "A", label: "Accessible" },
  { key: "interoperable", letter: "I", label: "Interoperable" },
  { key: "reusable", letter: "R", label: "Reusable" },
];

export function fairScore(fair: FairFlags): number {
  return FAIR_AXES.reduce((n, a) => n + (fair[a.key] ? 1 : 0), 0);
}

/**
 * Compact four-dot FAIR indicator. Each dot maps to one of the FAIR principles
 * (Findable, Accessible, Interoperable, Reusable). Lit dots use the signature
 * auralis colour; unmet axes fade out.
 */
export function FairDots({ fair, className }: { fair: FairFlags; className?: string }) {
  return (
    <div className={cn("flex items-center gap-1", className)} title={`FAIR ${fairScore(fair)}/4`}>
      {FAIR_AXES.map((a) => (
        <span
          key={a.key}
          aria-label={`${a.label}: ${fair[a.key] ? "met" : "unmet"}`}
          className={cn(
            "h-1.5 w-1.5 rounded-full transition-colors",
            fair[a.key] ? "bg-auralis shadow-[0_0_6px_rgba(22,224,196,0.6)]" : "bg-veil-3",
          )}
        />
      ))}
    </div>
  );
}

/**
 * Full FAIR breakdown with one labelled row per principle. Used on the dataset
 * detail page where the reasoning behind each axis matters.
 */
export function FairBreakdown({ fair }: { fair: FairFlags }) {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {FAIR_AXES.map((a) => (
        <div
          key={a.key}
          className={cn(
            "flex items-center gap-2.5 rounded-md border px-3 py-2.5 transition-colors",
            fair[a.key] ? "border-auralis/25 bg-auralis/[0.06]" : "border-hairline bg-veil-2/40",
          )}
        >
          <span
            className={cn(
              "grid h-7 w-7 shrink-0 place-items-center rounded-md font-display text-[13px] font-semibold",
              fair[a.key] ? "bg-auralis/15 text-auralis" : "bg-veil-3 text-faint",
            )}
          >
            {a.letter}
          </span>
          <div className="min-w-0">
            <div className={cn("text-[12.5px] font-medium", fair[a.key] ? "text-lumen" : "text-muted")}>{a.label}</div>
            <div className="text-[10.5px] text-faint">{fair[a.key] ? "Conformant" : "Gap identified"}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
