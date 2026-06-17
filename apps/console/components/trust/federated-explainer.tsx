import { Network, Lock, ArrowRight, Layers } from "lucide-react";
import { Badge } from "@/components/ui/primitives";

/**
 * Federated-learning explainer. The differentiating claim: raw data never
 * leaves its jurisdiction — only encrypted, privacy-clipped gradients are
 * aggregated centrally. This card visualizes three jurisdiction-local
 * trainers feeding a secure aggregator that returns a shared model.
 */
const NODES = [
  { region: "eu-north", label: "EU", rows: "6.3M", tone: "auralis" as const },
  { region: "us-west", label: "US", rows: "920M", tone: "ion" as const },
  { region: "ap-south", label: "APAC", rows: "88M", tone: "solar" as const },
];

export function FederatedExplainer() {
  return (
    <div className="space-y-4">
      <p className="text-[12.5px] leading-relaxed text-muted">
        Models train <span className="text-lumen">where the data lives</span>. Each jurisdiction runs a local trainer
        on its own residency-bound partition; only differentially-private, encrypted gradient updates cross the wire to
        a secure aggregator. The raw rows never move — residency and PII guarantees are preserved end-to-end.
      </p>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        {/* Local trainers */}
        <div className="space-y-2">
          {NODES.map((n) => (
            <div
              key={n.region}
              className="flex items-center justify-between gap-2 rounded-md border border-hairline bg-veil-2/60 px-2.5 py-2"
            >
              <div className="flex items-center gap-2">
                <Lock size={13} className="text-verdant/80" />
                <div className="leading-tight">
                  <div className="text-[11.5px] font-medium text-lumen">{n.label} node</div>
                  <div className="font-mono text-[9.5px] text-faint">{n.region}</div>
                </div>
              </div>
              <span className="tabular-nums text-[10.5px] text-muted">{n.rows} rows</span>
            </div>
          ))}
        </div>

        {/* Gradient flow */}
        <div className="flex flex-col items-center gap-1 px-1">
          <ArrowRight size={16} className="text-auralis/70" />
          <span className="whitespace-nowrap text-[9px] uppercase tracking-wider text-faint">∇ only</span>
        </div>

        {/* Aggregator */}
        <div className="flex h-full flex-col items-center justify-center gap-2 rounded-md border border-auralis/30 bg-auralis/5 p-3 text-center">
          <span className="grid h-9 w-9 place-items-center rounded-md border border-auralis/30 bg-veil-2 text-auralis">
            <Layers size={16} />
          </span>
          <div className="text-[12px] font-medium text-lumen">Secure aggregator</div>
          <div className="text-[10px] leading-snug text-faint">FedAvg over encrypted gradients</div>
          <Badge tone="verdant" dot>
            data stays put
          </Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-hairline pt-3 text-[11px] text-muted">
        <Network size={13} className="text-auralis/70" />
        <span>Zero cross-border row movement</span>
        <span className="text-hairline">·</span>
        <span>Secure aggregation (SMPC)</span>
        <span className="text-hairline">·</span>
        <span>DP-clipped updates (ε ≤ 1.0)</span>
      </div>
    </div>
  );
}
