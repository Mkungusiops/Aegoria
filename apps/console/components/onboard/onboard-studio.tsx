"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileUp,
  Hammer,
  Link2,
  Loader2,
  Lock,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { Badge, Button, Card, ProgressBar, SectionHeader } from "@/components/ui/primitives";

type Mode = "upload" | "source";
type State = "idle" | "running" | "done" | "error";

interface OnboardResult {
  source: string;
  connector: string;
  dataset: string;
  assessment: {
    row_estimate: number;
    sampled_rows: number;
    truncated: boolean;
    column_count: number;
    duplicate_rows: number;
    completeness: number;
    overall_quality_score: number;
    pii_columns: string[];
    issues_summary: string[];
    columns: { name: string; inferred_type: string; pii: boolean; issues: string[] }[];
  };
  cleaning: {
    input_rows: number;
    output_rows: number;
    input_quality_score: number;
    output_quality_score: number;
    steps_applied: { op: string; notes: string; cells_changed: number; rows_removed: number; columns_added: string[] }[];
  };
  outputs: Record<string, string>;
  landed_dataset: string | null;
  ai_bundle: {
    chunk_count: number;
    rows_serialized: number;
    masked_fields: string[];
    signature: string | null;
  } | null;
}

export function OnboardStudio() {
  const [mode, setMode] = React.useState<Mode>("upload");
  const [file, setFile] = React.useState<File | null>(null);
  const [source, setSource] = React.useState("");
  const [dataset, setDataset] = React.useState("");
  const [land, setLand] = React.useState(true);
  const [ai, setAi] = React.useState(true);
  const [state, setState] = React.useState<State>("idle");
  const [result, setResult] = React.useState<OnboardResult | null>(null);
  const [error, setError] = React.useState<string>("");
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const canRun = mode === "upload" ? !!file : source.trim().length > 0;

  async function run() {
    setState("running");
    setError("");
    setResult(null);
    try {
      let res: Response;
      if (mode === "upload" && file) {
        const params = new URLSearchParams({
          filename: file.name,
          land: String(land),
          ai: String(ai),
        });
        if (dataset.trim()) params.set("dataset", dataset.trim());
        res = await fetch(`/api/onboard?${params.toString()}`, { method: "POST", body: file });
      } else {
        res = await fetch("/api/onboard", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ source: source.trim(), dataset: dataset.trim() || null, land, ai }),
        });
      }
      const payload = await res.json();
      if (!res.ok) {
        setError(payload?.detail ? String(payload.detail) : `request failed (${res.status})`);
        setState("error");
        return;
      }
      setResult(payload as OnboardResult);
      setState("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  }

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.95fr_1.05fr]">
      {/* ---------------------------------------------------------- Input */}
      <div className="space-y-4">
        <Card>
          <SectionHeader
            title="Source"
            subtitle="Upload a file or point at a server-side database/file. It is profiled, cleaned and (optionally) landed as a governed dataset."
            icon={<UploadCloud size={16} />}
          />

          {/* mode toggle */}
          <div className="mt-4 inline-flex rounded-md border border-hairline bg-veil-2/50 p-0.5 text-[12.5px]">
            {(["upload", "source"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`inline-flex items-center gap-1.5 rounded-[5px] px-3 py-1.5 font-medium transition-colors ${
                  mode === m ? "bg-auralis/15 text-auralis" : "text-muted hover:text-lumen"
                }`}
              >
                {m === "upload" ? <FileUp size={13} /> : <Link2 size={13} />}
                {m === "upload" ? "Upload a file" : "Connect a source"}
              </button>
            ))}
          </div>

          {mode === "upload" ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
              }}
              onClick={() => inputRef.current?.click()}
              className={`mt-3 grid cursor-pointer place-items-center rounded-md border border-dashed px-4 py-9 text-center transition-colors ${
                dragging ? "border-auralis/60 bg-auralis/[0.06]" : "border-hairline bg-veil-2/20 hover:border-auralis/40"
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.tsv,.parquet,.json,.ndjson,.jsonl,.db,.sqlite,.sqlite3"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <UploadCloud size={24} className={dragging ? "text-auralis" : "text-faint"} />
              {file ? (
                <p className="mt-2 text-[13px] font-medium text-lumen">{file.name}</p>
              ) : (
                <>
                  <p className="mt-2 text-[13px] font-medium text-lumen">Drop a file or click to browse</p>
                  <p className="mt-1 text-[11.5px] text-muted">CSV · Parquet · JSON · SQLite</p>
                </>
              )}
            </div>
          ) : (
            <div className="mt-3">
              <label className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-wider text-faint">
                Path or connection string
              </label>
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="/data/customers.sqlite  ·  postgresql://host/db  ·  /path/to/file.csv"
                className="w-full rounded-md border border-hairline bg-veil-2/40 px-3 py-2 font-mono text-[12.5px] text-lumen outline-none placeholder:text-faint focus:border-auralis/40"
              />
              <p className="mt-1.5 text-[11px] text-faint">Resolved on the API host (server-side files / reachable databases).</p>
            </div>
          )}

          {/* options */}
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-wider text-faint">Dataset name</label>
              <input
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                placeholder="(auto from source)"
                className="w-full rounded-md border border-hairline bg-veil-2/40 px-3 py-2 text-[12.5px] text-lumen outline-none placeholder:text-faint focus:border-auralis/40"
              />
            </div>
            <div className="flex items-end gap-4 pb-1">
              <Toggle label="Land in lakehouse" checked={land} onChange={setLand} />
              <Toggle label="AI bundle" checked={ai} onChange={setAi} />
            </div>
          </div>

          <div className="mt-5 flex items-center justify-between">
            <p className="text-[11px] text-faint">
              <Lock size={11} className="mr-1 inline" />
              PII is auto-classified and masked before any AI export.
            </p>
            <Button variant="primary" onClick={run} disabled={!canRun || state === "running"}>
              {state === "running" ? <Loader2 size={14} className="animate-spin" /> : <Hammer size={14} />}
              {state === "running" ? "Onboarding…" : "Assess & Clean"}
            </Button>
          </div>
        </Card>

        {state === "error" && (
          <div className="flex items-start gap-3 rounded-md border border-crimson/30 bg-crimson/[0.06] px-4 py-4">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-crimson" />
            <div>
              <div className="text-[13px] font-semibold text-crimson">Onboarding failed</div>
              <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* --------------------------------------------------------- Results */}
      <div className="lg:sticky lg:top-6 lg:self-start">
        {result ? (
          <ResultPanel result={result} />
        ) : (
          <Placeholder running={state === "running"} />
        )}
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!checked)} className="inline-flex items-center gap-2 text-[12.5px] text-muted">
      <span
        className={`relative h-4 w-7 rounded-full transition-colors ${checked ? "bg-auralis/70" : "bg-veil-3"}`}
      >
        <span
          className={`absolute top-0.5 h-3 w-3 rounded-full bg-lumen transition-all ${checked ? "left-3.5" : "left-0.5"}`}
        />
      </span>
      {label}
    </button>
  );
}

function ResultPanel({ result }: { result: OnboardResult }) {
  const a = result.assessment;
  const c = result.cleaning;
  const removed = c.input_rows - c.output_rows;
  return (
    <div className="animate-fade-up space-y-4">
      <Card glow>
        <SectionHeader
          title={
            <span className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-verdant" /> {result.dataset}
            </span>
          }
          subtitle={`Onboarded from ${result.connector} source`}
          icon={<Database size={16} />}
        />
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Metric label="Rows" value={`${c.input_rows} → ${c.output_rows}`} hint={removed > 0 ? `${removed} removed` : "no rows dropped"} />
          <Metric label="Quality" value={`${a.overall_quality_score.toFixed(2)} → ${c.output_quality_score.toFixed(2)}`} hint="before → after" tone="verdant" />
          <Metric label="Duplicates" value={String(a.duplicate_rows)} hint="rows" />
          <Metric label="PII columns" value={String(a.pii_columns.length)} hint={a.pii_columns.length ? "masked for AI" : "none"} tone={a.pii_columns.length ? "pulse" : "neutral"} />
        </div>
        {a.truncated && (
          <p className="mt-3 text-[11px] text-solar">
            Sampled {a.sampled_rows.toLocaleString()} of {a.row_estimate.toLocaleString()} rows (truncated for this run).
          </p>
        )}
      </Card>

      {/* Assessment */}
      <Card>
        <SectionHeader title="Assessment" subtitle="What the profiler found" icon={<Sparkles size={15} />} />
        {a.issues_summary.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {a.issues_summary.map((iss, i) => (
              <li key={i} className="flex items-start gap-2 text-[12.5px] text-muted">
                <AlertTriangle size={13} className="mt-0.5 shrink-0 text-solar" />
                {iss}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-4 overflow-hidden rounded-md border border-hairline">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-hairline bg-veil-2/60 text-left text-[10.5px] uppercase tracking-wider text-faint">
                <th className="px-3 py-2 font-medium">Column</th>
                <th className="px-3 py-2 font-medium">Type</th>
                <th className="px-3 py-2 font-medium">Findings</th>
              </tr>
            </thead>
            <tbody>
              {a.columns.map((col) => (
                <tr key={col.name} className="border-b border-hairline/60 last:border-0">
                  <td className="px-3 py-2 font-medium text-lumen">
                    <span className="flex items-center gap-1.5">
                      {col.name}
                      {col.pii && <Badge tone="pulse">PII</Badge>}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted">{col.inferred_type}</td>
                  <td className="px-3 py-2 text-[11.5px] text-muted">{col.issues.length ? col.issues.join("; ") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Cleaning */}
      <Card>
        <SectionHeader title="Cleaning applied" subtitle="Conservative, auditable transforms" icon={<Hammer size={15} />} />
        <ProgressBar value={c.output_quality_score * 100} tone="verdant" className="mt-3" />
        <ul className="mt-4 space-y-2">
          {c.steps_applied.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-[12.5px]">
              <Badge tone="auralis" className="shrink-0">{s.op}</Badge>
              <span className="text-muted">
                {s.notes}
                {(s.cells_changed > 0 || s.rows_removed > 0 || s.columns_added.length > 0) && (
                  <span className="text-faint">
                    {" "}·{s.cells_changed ? ` ${s.cells_changed} cells` : ""}
                    {s.rows_removed ? ` ${s.rows_removed} rows` : ""}
                    {s.columns_added.length ? ` +${s.columns_added.join(", ")}` : ""}
                  </span>
                )}
              </span>
            </li>
          ))}
          {c.steps_applied.length === 0 && <li className="text-[12.5px] text-muted">Data was already clean — no transforms needed.</li>}
        </ul>
      </Card>

      {/* Outputs + AI */}
      <Card>
        <SectionHeader title="Outputs" subtitle="Use internally, in another app, or feed to an AI" icon={<ShieldCheck size={15} />} />
        <div className="mt-3 space-y-2 text-[12px]">
          {Object.entries(result.outputs).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3 rounded-md border border-hairline bg-veil-2/30 px-3 py-2">
              <span className="font-medium text-muted">{k}</span>
              <span className="truncate font-mono text-[11px] text-faint" title={v}>{v}</span>
            </div>
          ))}
        </div>
        {result.ai_bundle && (
          <div className="mt-3 rounded-md border border-pulse/30 bg-pulse/[0.05] px-3 py-3">
            <div className="flex items-center gap-2 text-[12.5px] font-medium text-[#b3a4ff]">
              <Sparkles size={14} /> AI-ready bundle
              {result.ai_bundle.signature && <Badge tone="verdant" dot>signed</Badge>}
            </div>
            <p className="mt-1 text-[11.5px] text-muted">
              {result.ai_bundle.chunk_count.toLocaleString()} documents · masked fields:{" "}
              {result.ai_bundle.masked_fields.length ? result.ai_bundle.masked_fields.join(", ") : "none"}.
            </p>
          </div>
        )}
        {result.landed_dataset && (
          <a
            href="/catalog"
            className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-auralis hover:underline"
          >
            <Database size={13} /> View governed dataset · {result.landed_dataset}
          </a>
        )}
      </Card>
    </div>
  );
}

function Metric({ label, value, hint, tone = "auralis" }: { label: string; value: string; hint?: string; tone?: "auralis" | "verdant" | "pulse" | "neutral" }) {
  const color = { auralis: "text-lumen", verdant: "text-verdant", pulse: "text-[#b3a4ff]", neutral: "text-muted" }[tone];
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10.5px] font-medium uppercase tracking-wider text-faint">{label}</span>
      <span className={`font-display text-[16px] font-semibold tabular-nums ${color}`}>{value}</span>
      {hint && <span className="text-[10.5px] text-faint">{hint}</span>}
    </div>
  );
}

function Placeholder({ running }: { running: boolean }) {
  return (
    <div className="surface-2 grid place-items-center px-5 py-20 text-center">
      <div className="grid h-11 w-11 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
        {running ? <Loader2 size={18} className="animate-spin" /> : <UploadCloud size={18} />}
      </div>
      <p className="mt-3 text-[13px] font-medium text-lumen">
        {running ? "Profiling · cleaning · masking PII…" : "Onboarding results appear here"}
      </p>
      <p className="mt-1 max-w-[36ch] text-[12px] leading-relaxed text-muted">
        {running
          ? "Connecting to the source, assessing quality and PII, applying the cleaning plan, and emitting cleaned + AI-ready outputs."
          : "Connect a source and run it — you'll get a quality + PII assessment, the cleaning audit, a governed dataset, and a PII-masked AI corpus."}
      </p>
    </div>
  );
}
