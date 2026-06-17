import { Radio, Clock } from "lucide-react";
import type { Pipeline } from "@/lib/types";
import { Badge } from "@/components/ui/primitives";
import { Sparkline } from "@/components/ui/charts";
import { fmtNum } from "@/lib/data";
import {
  STATUS_META,
  MODALITY_META,
  TONE_TEXT,
  fmtFreshness,
  fmtSchedule,
  fmtAgo,
  freshnessSlo,
} from "./pipeline-utils";

/**
 * One pipeline expressed as a dense, scannable row: identity, modality, cadence,
 * live throughput sparkline, records/min and a freshness SLO verdict. Designed
 * to read at a glance whether multi-modal ingestion is keeping pace.
 */
export function PipelineRow({ p }: { p: Pipeline }) {
  const status = STATUS_META[p.status];
  const modality = MODALITY_META[p.modality];
  const slo = freshnessSlo(p.schedule, p.freshnessSec);
  const streaming = p.schedule === "streaming";

  return (
    <div className="grid grid-cols-12 items-center gap-3 rounded-md border border-hairline bg-veil-2/40 px-3.5 py-3 transition-colors hover:border-auralis/30">
      {/* Identity + modality */}
      <div className="col-span-12 flex items-center gap-3 lg:col-span-4">
        <span
          className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border border-hairline bg-veil-2 ${TONE_TEXT[modality.tone]}`}
        >
          {streaming ? <Radio size={15} /> : <Clock size={15} />}
        </span>
        <div className="min-w-0">
          <div className="truncate text-[13px] font-medium text-lumen">{p.name}</div>
          <div className="mt-0.5 flex items-center gap-2">
            <Badge tone={modality.tone}>{modality.label}</Badge>
            <span className="truncate text-[11px] text-faint">{fmtSchedule(p.schedule)}</span>
          </div>
        </div>
      </div>

      {/* Throughput sparkline */}
      <div className="col-span-6 lg:col-span-3">
        <Sparkline
          data={p.throughput}
          color={status.tone === "crimson" ? "crimson" : status.tone === "solar" ? "solar" : "auralis"}
          className="w-full"
          width={200}
          height={34}
        />
      </div>

      {/* Records/min */}
      <div className="col-span-3 lg:col-span-2">
        <div className="text-[13px] font-semibold tabular-nums text-lumen">{fmtNum(p.recordsPerMin)}</div>
        <div className="text-[10.5px] uppercase tracking-wider text-faint">rec / min</div>
      </div>

      {/* Freshness */}
      <div className="col-span-3 lg:col-span-2">
        <div
          className={`text-[13px] font-semibold tabular-nums ${slo.withinSlo ? "text-verdant" : "text-solar"}`}
        >
          {fmtFreshness(p.freshnessSec)}
        </div>
        <div className="text-[10.5px] uppercase tracking-wider text-faint">
          {slo.withinSlo ? `≤ ${slo.targetLabel} SLO` : `> ${slo.targetLabel} SLO`}
        </div>
      </div>

      {/* Status */}
      <div className="col-span-12 flex items-center justify-between lg:col-span-1 lg:justify-end">
        <Badge tone={status.tone} dot>
          {status.label}
        </Badge>
        <span className="text-[10.5px] text-faint lg:hidden">{fmtAgo(p.lastRun)}</span>
      </div>
    </div>
  );
}
