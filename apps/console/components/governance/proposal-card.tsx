import { Users, Clock, CheckCircle2, XCircle, Vote } from "lucide-react";
import type { CommonsProposal } from "@/lib/types";
import { Badge, Button } from "@/components/ui/primitives";
import type { Tone } from "@/components/ui/primitives";

const STATUS_META: Record<
  CommonsProposal["status"],
  { tone: Tone; label: string; icon: typeof Vote }
> = {
  open: { tone: "auralis", label: "open for vote", icon: Vote },
  passed: { tone: "verdant", label: "passed", icon: CheckCircle2 },
  rejected: { tone: "crimson", label: "rejected", icon: XCircle },
};

/**
 * A participatory-governance proposal. Shows the for/against split as a dual bar,
 * participation count and a quorum/threshold readout so communities can see the
 * weight of their stake. Voting controls are present (disabled in the console).
 */
export function ProposalCard({ p }: { p: CommonsProposal }) {
  const meta = STATUS_META[p.status];
  const StatusIcon = meta.icon;
  const open = p.status === "open";
  const passing = p.forPct >= 60; // governance charter threshold

  return (
    <div
      className={`surface flex flex-col p-5 transition-shadow duration-300 ${
        open ? "hover:border-auralis/30" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
            <span className="font-mono">{p.id}</span>
            <span>·</span>
            <span>{p.proposer}</span>
          </div>
          <h3 className="mt-1 text-[14px] font-semibold leading-snug text-lumen">{p.title}</h3>
        </div>
        <Badge tone={meta.tone} dot>
          {meta.label}
        </Badge>
      </div>

      <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{p.summary}</p>

      {/* For / against dual bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-[11.5px]">
          <span className="text-verdant">For {p.forPct}%</span>
          <span className="text-faint">Against {100 - p.forPct}%</span>
        </div>
        <div className="mt-1.5 flex h-2 w-full overflow-hidden rounded-full bg-veil-3">
          <div
            className="h-full bg-verdant transition-all duration-700"
            style={{ width: `${p.forPct}%` }}
          />
          <div className="h-full flex-1 bg-crimson/50" />
        </div>
        <div className="mt-1.5 flex items-center justify-between text-[10.5px] text-faint">
          <span className={passing ? "text-verdant" : "text-solar"}>
            {passing ? "above" : "below"} 60% threshold
          </span>
          <span>simple-majority charter</span>
        </div>
      </div>

      {/* Footer: participation + timing + action */}
      <div className="mt-4 flex items-center justify-between border-t border-hairline pt-3">
        <div className="flex items-center gap-4 text-[11.5px] text-muted">
          <span className="inline-flex items-center gap-1.5">
            <Users size={13} className="text-faint" /> {p.participants} voters
          </span>
          <span className="inline-flex items-center gap-1.5">
            {open ? (
              <>
                <Clock size={13} className="text-faint" /> closes in {p.closesIn}
              </>
            ) : (
              <>
                <StatusIcon size={13} className={meta.tone === "verdant" ? "text-verdant" : "text-crimson"} />{" "}
                {p.closesIn}
              </>
            )}
          </span>
        </div>
        {open ? (
          <div className="flex gap-2">
            <Button variant="default" className="px-3 py-1.5 text-[12px]" disabled>
              Abstain
            </Button>
            <Button variant="primary" className="px-3 py-1.5 text-[12px]" disabled>
              <Vote size={13} /> Cast stake
            </Button>
          </div>
        ) : (
          <Button variant="ghost" className="px-3 py-1.5 text-[12px]" disabled>
            View result
          </Button>
        )}
      </div>
    </div>
  );
}
