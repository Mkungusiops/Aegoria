"use client";

import * as React from "react";
import {
  AlertTriangle,
  Clock,
  Database,
  HardDrive,
  Play,
  Sparkles,
  TableProperties,
  UserRound,
} from "lucide-react";
import { Badge, Button, Card, SectionHeader } from "@/components/ui/primitives";
import { fmtBytes, fmtNum } from "@/lib/data";
import { GovernanceReceipt } from "./receipt";
import type { QueryExample } from "./examples";

type RunState = "idle" | "running" | "done";

/**
 * Query Studio — a governed SQL surface. Selecting an example loads its stored
 * SQL; "Run (governed)" simulates the engine round-trip and then surfaces the
 * result preview alongside the all-important Governance Receipt. No live backend
 * is required: results and receipts come from the canonical query-run fixtures.
 */
export function QueryStudio({ examples }: { examples: QueryExample[] }) {
  const [selectedId, setSelectedId] = React.useState(examples[0]?.id ?? "");
  const selected = React.useMemo(
    () => examples.find((e) => e.id === selectedId) ?? examples[0],
    [examples, selectedId],
  );
  const [sql, setSql] = React.useState(selected?.sql ?? "");
  const [state, setState] = React.useState<RunState>("idle");
  const [shown, setShown] = React.useState<QueryExample | null>(null);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const pickExample = (id: string) => {
    const ex = examples.find((e) => e.id === id);
    if (!ex) return;
    setSelectedId(id);
    setSql(ex.sql);
    setState("idle");
    setShown(null);
  };

  const run = () => {
    if (!selected) return;
    setState("running");
    setShown(null);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setShown(selected);
      setState("done");
    }, 620);
  };

  const dirty = selected ? sql.trim() !== selected.sql.trim() : false;

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.55fr_1fr]">
      {/* Editor + results */}
      <div className="space-y-4">
        {/* Example chooser */}
        <Card className="!p-0">
          <div className="flex flex-wrap items-center gap-2 border-b border-hairline px-4 py-3">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">
              <Sparkles size={13} /> Examples
            </span>
            {examples.map((e) => (
              <button
                key={e.id}
                onClick={() => pickExample(e.id)}
                className={`rounded-full border px-2.5 py-1 text-[11.5px] font-medium transition-colors ${
                  selectedId === e.id
                    ? "border-auralis/40 bg-auralis/10 text-auralis"
                    : "border-hairline bg-veil-2/50 text-muted hover:border-auralis/30 hover:text-lumen"
                }`}
              >
                {e.title}
              </button>
            ))}
          </div>

          {/* Code editor surface */}
          <div className="relative">
            <div className="flex items-center justify-between border-b border-hairline bg-veil-2/40 px-4 py-2">
              <div className="flex items-center gap-2 text-[11.5px] text-faint">
                <Database size={13} />
                <span className="font-mono">governed.sql</span>
                {dirty && <Badge tone="solar">edited</Badge>}
              </div>
              <span className="font-mono text-[10.5px] text-faint">SQL · ANSI</span>
            </div>
            <div className="relative font-mono">
              <textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                spellCheck={false}
                rows={6}
                className="block w-full resize-y bg-transparent px-4 py-3.5 font-mono text-[13px] leading-relaxed text-lumen caret-auralis outline-none placeholder:text-faint"
                placeholder="SELECT … FROM dataset WHERE …"
              />
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-hairline bg-veil-2/40 px-4 py-3">
              <div className="flex items-center gap-2 text-[11.5px] text-faint">
                <UserRound size={13} />
                principal <span className="font-medium text-muted">{selected?.principal ?? "—"}</span>
              </div>
              <Button variant="primary" onClick={run} disabled={state === "running" || sql.trim().length === 0}>
                <Play size={14} />
                {state === "running" ? "Running…" : "Run (governed)"}
              </Button>
            </div>
          </div>
        </Card>

        {/* Results */}
        <Card>
          <SectionHeader
            title="Results"
            subtitle="Rows are only returned after authorization, placement and privacy obligations are applied."
            icon={<TableProperties size={16} />}
            action={
              shown && shown.status === "ok" ? (
                <div className="flex items-center gap-3 text-[11px] text-faint">
                  <span className="inline-flex items-center gap-1">
                    <Clock size={11} /> {shown.durationMs} ms
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <HardDrive size={11} /> {fmtBytes(shown.bytesScanned)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Database size={11} /> {fmtNum(shown.rows)} rows
                  </span>
                </div>
              ) : undefined
            }
          />
          <div className="mt-4">
            <ResultsBody state={state} example={shown} />
          </div>
        </Card>
      </div>

      {/* Governance receipt — the differentiator */}
      <div className="lg:sticky lg:top-6 lg:self-start">
        {shown ? (
          <div className="animate-fade-up">
            <GovernanceReceipt example={shown} />
          </div>
        ) : (
          <ReceiptPlaceholder running={state === "running"} />
        )}
      </div>
    </div>
  );
}

function ResultsBody({ state, example }: { state: RunState; example: QueryExample | null }) {
  if (state === "running") {
    return (
      <div className="grid place-items-center rounded-md border border-hairline bg-veil-2/30 py-14 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-hairline border-t-auralis" />
        <p className="mt-3 text-[12.5px] text-muted">Authorizing · placing for low carbon · enforcing privacy…</p>
      </div>
    );
  }

  if (!example) {
    return (
      <div className="grid place-items-center rounded-md border border-dashed border-hairline bg-veil-2/20 py-14 text-center">
        <TableProperties size={26} className="text-faint" />
        <p className="mt-3 text-[13px] font-medium text-lumen">Run a query to see governed results</p>
        <p className="mt-1 text-[12px] text-muted">Pick an example above, or write your own, then Run (governed).</p>
      </div>
    );
  }

  if (example.status === "denied" || !example.result) {
    return (
      <div className="flex items-start gap-3 rounded-md border border-crimson/30 bg-crimson/[0.06] px-4 py-4">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-crimson" />
        <div>
          <div className="text-[13px] font-semibold text-crimson">Query denied — no rows returned</div>
          <p className="mt-1 text-[12.5px] leading-relaxed text-muted">
            The governance service blocked this query before execution. See the receipt for the controlling policy. Rewrite
            it as an aggregate, or request elevated clearance.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-hairline">
      <table className="w-full text-[12.5px]">
        <thead>
          <tr className="border-b border-hairline bg-veil-2/60 text-left text-[11px] uppercase tracking-wider text-faint">
            {example.result.columns.map((c) => (
              <th key={c} className="px-3 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {example.result.rows.map((row, ri) => (
            <tr key={ri} className="border-b border-hairline/60 last:border-0 hover:bg-veil-2/40">
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-2.5 tabular-nums text-lumen">
                  {typeof cell === "number" ? cell.toLocaleString("en-US") : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {example.dpApplied && (
        <div className="border-t border-hairline bg-pulse/[0.05] px-3 py-2 text-[11px] text-[#b3a4ff]">
          Differentially-private result — calibrated noise added at ε {example.epsilonSpent}. Exact values are never exposed.
        </div>
      )}
    </div>
  );
}

function ReceiptPlaceholder({ running }: { running: boolean }) {
  return (
    <div className="surface-2 grid place-items-center px-5 py-16 text-center">
      <div className="grid h-11 w-11 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
        <Sparkles size={18} />
      </div>
      <p className="mt-3 text-[13px] font-medium text-lumen">Governance receipt appears here</p>
      <p className="mt-1 max-w-[34ch] text-[12px] leading-relaxed text-muted">
        {running
          ? "Composing the authorize decision, carbon placement and privacy budget…"
          : "Every governed query returns a verifiable receipt: engine + region, carbon grams, DP epsilon, masked columns and the authorize decision."}
      </p>
    </div>
  );
}
