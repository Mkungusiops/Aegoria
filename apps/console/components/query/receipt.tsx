import {
  CheckCircle2,
  Cpu,
  EyeOff,
  Gauge,
  Leaf,
  MapPin,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import { Badge, Divider } from "@/components/ui/primitives";
import type { QueryExample } from "./examples";

/**
 * The Governance Receipt — Aegoria's signature artifact. Every governed query
 * returns not just rows but a verifiable account of how it was authorized,
 * where it was placed for the lowest carbon, what privacy budget it consumed
 * and which columns were masked. This is the platform's core differentiator,
 * so it is rendered prominently rather than tucked into a tooltip.
 */
export function GovernanceReceipt({ example }: { example: QueryExample }) {
  const denied = example.status === "denied";
  return (
    <div className="surface-2 overflow-hidden">
      {/* Receipt header */}
      <div
        className={`flex items-center justify-between gap-3 border-b border-hairline px-4 py-3 ${
          denied ? "bg-crimson/[0.06]" : "bg-auralis/[0.05]"
        }`}
      >
        <div className="flex items-center gap-2.5">
          <span
            className={`grid h-8 w-8 place-items-center rounded-md ${
              denied ? "bg-crimson/15 text-crimson" : "bg-auralis/15 text-auralis"
            }`}
          >
            {denied ? <ShieldX size={16} /> : <ShieldCheck size={16} />}
          </span>
          <div>
            <div className="text-[13px] font-semibold text-lumen">Governance receipt</div>
            <div className="font-mono text-[10.5px] text-faint">{example.id}</div>
          </div>
        </div>
        <Badge tone={denied ? "crimson" : "verdant"} dot>
          {denied ? "denied" : "authorized"}
        </Badge>
      </div>

      {/* Authorization rationale */}
      <div className="px-4 py-3.5">
        <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-faint">
          <CheckCircle2 size={12} /> Authorize decision
        </div>
        <p className={`mt-1.5 text-[12.5px] leading-relaxed ${denied ? "text-crimson" : "text-muted"}`}>
          {example.authorization}
        </p>
      </div>

      <Divider />

      {/* Receipt metric grid */}
      <div className="grid grid-cols-2 divide-x divide-hairline border-b border-hairline">
        <ReceiptCell
          icon={<Cpu size={14} />}
          label="Engine"
          value={example.engine === "—" ? "not placed" : example.engine}
          muted={example.engine === "—"}
        />
        <ReceiptCell
          icon={<MapPin size={14} />}
          label="Region"
          value={example.region === "—" ? "not placed" : example.region}
          muted={example.region === "—"}
        />
      </div>
      <div className="grid grid-cols-2 divide-x divide-hairline border-b border-hairline">
        <ReceiptCell
          icon={<Leaf size={14} className="text-verdant" />}
          label="Carbon"
          value={example.carbonG > 0 ? `${example.carbonG} gCO₂` : "—"}
          tone="verdant"
          muted={example.carbonG === 0}
        />
        <ReceiptCell
          icon={<Gauge size={14} className="text-pulse" />}
          label="DP epsilon"
          value={example.dpApplied ? `ε ${example.epsilonSpent}` : "not applied"}
          tone="pulse"
          muted={!example.dpApplied}
        />
      </div>

      {/* Masked columns */}
      <div className="px-4 py-3.5">
        <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-faint">
          <EyeOff size={12} /> Masked columns
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {example.maskedColumns.length > 0 ? (
            example.maskedColumns.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1 rounded border border-crimson/30 bg-crimson/10 px-1.5 py-0.5 font-mono text-[11px] text-crimson"
              >
                <EyeOff size={10} /> {c}
              </span>
            ))
          ) : (
            <span className="text-[11.5px] text-faint">No columns required masking</span>
          )}
        </div>
      </div>

      {/* Footer attestation */}
      <div className="border-t border-hairline bg-veil-2/40 px-4 py-2.5">
        <p className="flex items-center gap-1.5 text-[10.5px] text-faint">
          <ShieldCheck size={11} className="text-auralis" />
          Signed by the governance service before any rows were returned.
        </p>
      </div>
    </div>
  );
}

function ReceiptCell({
  icon,
  label,
  value,
  tone,
  muted = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "verdant" | "pulse";
  muted?: boolean;
}) {
  const valueClass = muted ? "text-faint" : tone === "verdant" ? "text-verdant" : tone === "pulse" ? "text-pulse" : "text-lumen";
  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-faint">
        {icon} {label}
      </div>
      <div className={`mt-1 font-display text-[16px] font-semibold tabular-nums ${valueClass}`}>{value}</div>
    </div>
  );
}
