import { Panel, ProgressBar, Badge } from "@/components/ui/primitives";
import type { PrivacyBudget } from "@/lib/types";

/**
 * Differential-privacy budget ledger. Every subject↔dataset pair holds a
 * finite ε allowance; each DP query debits it. When the budget is exhausted,
 * the engine refuses further queries rather than risk re-identification. Bars
 * show spent (filled) vs remaining; near-exhausted budgets escalate to solar /
 * crimson.
 */
function tone(fraction: number) {
  if (fraction >= 0.85) return "crimson" as const;
  if (fraction >= 0.6) return "solar" as const;
  return "auralis" as const;
}

export function PrivacyBudgets({ budgets }: { budgets: PrivacyBudget[] }) {
  return (
    <div className="space-y-3">
      {budgets.map((b) => {
        const frac = b.epsilon ? b.spent / b.epsilon : 0;
        const remaining = Math.max(0, b.epsilon - b.spent);
        const t = tone(frac);
        return (
          <Panel key={`${b.subject}:${b.dataset}`} className="p-3.5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate font-mono text-[12px] text-lumen">{b.subject}</div>
                <div className="mt-0.5 truncate text-[10.5px] text-faint">{b.dataset}</div>
              </div>
              <Badge tone={t}>
                ε {remaining.toFixed(1)} left
              </Badge>
            </div>
            <ProgressBar value={frac * 100} tone={t} className="mt-3" />
            <div className="mt-1.5 flex items-center justify-between text-[10.5px] tabular-nums text-muted">
              <span>
                spent <span className="text-lumen">{b.spent.toFixed(1)}</span> ε
              </span>
              <span className="text-faint">budget {b.epsilon.toFixed(1)} ε</span>
            </div>
          </Panel>
        );
      })}
    </div>
  );
}
