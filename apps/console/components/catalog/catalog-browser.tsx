"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  Database,
  FileWarning,
  Filter,
  Search,
  ShieldAlert,
  X,
} from "lucide-react";
import { Badge, Button, Card, Panel } from "@/components/ui/primitives";
import { fmtBytes, fmtNum } from "@/lib/data";
import type { Dataset, Modality, Sensitivity } from "@/lib/types";
import { FairDots, fairScore } from "./fair";
import {
  MODALITY_LABEL,
  MODALITY_TONE,
  SENSITIVITY_LABEL,
  SENSITIVITY_TONE,
  TONE_HEX,
  TONE_TEXT,
  domainTone,
  qualityTone,
} from "./tokens";

/** The most sensitive classification present on a dataset (drives its risk badge). */
const SENSITIVITY_RANK: Sensitivity[] = [
  "public",
  "internal",
  "confidential",
  "financial",
  "pii",
  "phi",
  "restricted",
];

function topSensitivity(d: Dataset): Sensitivity {
  return d.fields.reduce<Sensitivity>((top, f) => {
    return SENSITIVITY_RANK.indexOf(f.sensitivity) > SENSITIVITY_RANK.indexOf(top) ? f.sensitivity : top;
  }, "public");
}

interface FilterRowProps {
  active: boolean;
  count: number;
  label: React.ReactNode;
  onClick: () => void;
}

function FilterRow({ active, count, label, onClick }: FilterRowProps) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[12.5px] transition-colors ${
        active
          ? "border-auralis/40 bg-auralis/10 text-lumen"
          : "border-transparent text-muted hover:border-hairline hover:bg-veil-2/50 hover:text-lumen"
      }`}
    >
      <span className="flex items-center gap-2">{label}</span>
      <span className="tabular-nums text-[11px] text-faint">{count}</span>
    </button>
  );
}

export function CatalogBrowser({ datasets }: { datasets: Dataset[] }) {
  const [query, setQuery] = React.useState("");
  const [domain, setDomain] = React.useState<string | null>(null);
  const [modality, setModality] = React.useState<Modality | null>(null);
  const [sensitivity, setSensitivity] = React.useState<Sensitivity | null>(null);
  const [signedOnly, setSignedOnly] = React.useState(false);

  const domains = React.useMemo(() => {
    const m = new Map<string, number>();
    for (const d of datasets) m.set(d.domain, (m.get(d.domain) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [datasets]);

  const modalities = React.useMemo(() => {
    const m = new Map<Modality, number>();
    for (const d of datasets) m.set(d.modality, (m.get(d.modality) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [datasets]);

  const sensitivities = React.useMemo(() => {
    const m = new Map<Sensitivity, number>();
    for (const d of datasets) {
      const top = topSensitivity(d);
      m.set(top, (m.get(top) ?? 0) + 1);
    }
    return [...m.entries()].sort((a, b) => SENSITIVITY_RANK.indexOf(b[0]) - SENSITIVITY_RANK.indexOf(a[0]));
  }, [datasets]);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return datasets.filter((d) => {
      if (domain && d.domain !== domain) return false;
      if (modality && d.modality !== modality) return false;
      if (sensitivity && topSensitivity(d) !== sensitivity) return false;
      if (signedOnly && !d.signed) return false;
      if (!q) return true;
      return (
        d.title.toLowerCase().includes(q) ||
        d.name.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q) ||
        d.tags.some((t) => t.toLowerCase().includes(q)) ||
        d.domain.toLowerCase().includes(q)
      );
    });
  }, [datasets, query, domain, modality, sensitivity, signedOnly]);

  const hasFilters = Boolean(domain || modality || sensitivity || signedOnly || query);
  const clearAll = () => {
    setQuery("");
    setDomain(null);
    setModality(null);
    setSensitivity(null);
    setSignedOnly(false);
  };

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[230px_1fr]">
      {/* Filter rail */}
      <aside className="lg:sticky lg:top-6 lg:self-start">
        <Panel className="p-4">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-[12px] font-medium uppercase tracking-wider text-faint">
              <Filter size={13} /> Filters
            </span>
            {hasFilters && (
              <button onClick={clearAll} className="flex items-center gap-1 text-[11px] text-auralis hover:underline">
                <X size={11} /> Clear
              </button>
            )}
          </div>

          <FilterSection title="Domain">
            {domains.map(([d, n]) => (
              <FilterRow
                key={d}
                active={domain === d}
                count={n}
                onClick={() => setDomain(domain === d ? null : d)}
                label={
                  <>
                    <span className="h-1.5 w-1.5 rounded-full bg-current" style={{ color: TONE_HEX[domainTone(d)] }} />
                    {d}
                  </>
                }
              />
            ))}
          </FilterSection>

          <FilterSection title="Modality">
            {modalities.map(([m, n]) => (
              <FilterRow
                key={m}
                active={modality === m}
                count={n}
                onClick={() => setModality(modality === m ? null : m)}
                label={MODALITY_LABEL[m]}
              />
            ))}
          </FilterSection>

          <FilterSection title="Sensitivity">
            {sensitivities.map(([s, n]) => (
              <FilterRow
                key={s}
                active={sensitivity === s}
                count={n}
                onClick={() => setSensitivity(sensitivity === s ? null : s)}
                label={
                  <>
                    <span className="h-1.5 w-1.5 rounded-full bg-current" style={{ color: TONE_HEX[SENSITIVITY_TONE[s]] }} />
                    {SENSITIVITY_LABEL[s]}
                  </>
                }
              />
            ))}
          </FilterSection>

          <FilterSection title="Provenance">
            <FilterRow
              active={signedOnly}
              count={datasets.filter((d) => d.signed).length}
              onClick={() => setSignedOnly((v) => !v)}
              label={
                <>
                  <BadgeCheck size={13} className="text-auralis" /> C2PA signed
                </>
              }
            />
          </FilterSection>
        </Panel>
      </aside>

      {/* Results */}
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-sm">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search datasets, tags, domains…"
              className="w-full rounded-md border border-hairline bg-veil-2/60 py-2 pl-9 pr-3 text-[13px] text-lumen placeholder:text-faint focus:border-auralis/40 focus:outline-none focus:ring-2 focus:ring-auralis/20"
            />
          </div>
          <div className="text-[12px] text-muted">
            <span className="font-medium text-lumen tabular-nums">{filtered.length}</span> of {datasets.length} datasets
          </div>
        </div>

        {/* Active filter chips */}
        {hasFilters && (
          <div className="flex flex-wrap items-center gap-1.5">
            {domain && <Chip onClear={() => setDomain(null)}>{domain}</Chip>}
            {modality && <Chip onClear={() => setModality(null)}>{MODALITY_LABEL[modality]}</Chip>}
            {sensitivity && <Chip onClear={() => setSensitivity(null)}>{SENSITIVITY_LABEL[sensitivity]}</Chip>}
            {signedOnly && <Chip onClear={() => setSignedOnly(false)}>Signed</Chip>}
            {query && <Chip onClear={() => setQuery("")}>“{query}”</Chip>}
          </div>
        )}

        {filtered.length === 0 ? (
          <Card className="grid place-items-center py-16 text-center">
            <Database size={28} className="text-faint" />
            <p className="mt-3 text-[14px] font-medium text-lumen">No datasets match these filters</p>
            <p className="mt-1 text-[12.5px] text-muted">Try widening your search or clearing filters.</p>
            <Button variant="default" className="mt-4" onClick={clearAll}>
              Clear all filters
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((d, i) => (
              <DatasetCard key={d.id} dataset={d} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DatasetCard({ dataset: d, index }: { dataset: Dataset; index: number }) {
  const top = topSensitivity(d);
  const href = `/catalog/${encodeURIComponent(d.id)}`;
  return (
    <Link href={href} className="group block animate-fade-up" style={{ animationDelay: `${Math.min(index * 40, 240)}ms` }}>
      <Card className="flex h-full flex-col transition-all duration-200 group-hover:-translate-y-0.5 group-hover:border-auralis/30 group-hover:shadow-glow">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <Badge tone={domainTone(d.domain)}>{d.domain}</Badge>
              <Badge tone={MODALITY_TONE[d.modality]}>{MODALITY_LABEL[d.modality]}</Badge>
            </div>
            <h3 className="mt-2.5 truncate font-display text-[15px] font-semibold text-lumen">{d.title}</h3>
            <p className="mt-0.5 font-mono text-[11px] text-faint">{d.name}</p>
          </div>
          <ArrowUpRight size={16} className="mt-0.5 shrink-0 text-faint transition-colors group-hover:text-auralis" />
        </div>

        <p className="mt-2.5 line-clamp-2 text-[12.5px] leading-relaxed text-muted">{d.description}</p>

        <div className="mt-4 flex items-center justify-between rounded-md border border-hairline bg-veil-2/40 px-3 py-2">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-wider text-faint">FAIR</span>
            <div className="flex items-center gap-1.5">
              <FairDots fair={d.fair} />
              <span className="text-[11px] tabular-nums text-muted">{fairScore(d.fair)}/4</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[10px] uppercase tracking-wider text-faint">Quality</span>
            <span className={`text-[13px] font-semibold tabular-nums ${TONE_TEXT[qualityTone(d.qualityScore)]}`}>
              {d.qualityScore.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[11.5px]">
          <Meta label="Rows" value={fmtNum(d.rows)} />
          <Meta label="Size" value={fmtBytes(d.bytes)} />
          <Meta label="Jurisdiction" value={d.jurisdiction} />
          <Meta
            label="PII fields"
            value={
              d.piiFields > 0 ? (
                <span className="inline-flex items-center gap-1 text-crimson">
                  <ShieldAlert size={11} /> {d.piiFields}
                </span>
              ) : (
                <span className="text-verdant">none</span>
              )
            }
          />
        </div>

        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          <div className="flex flex-wrap items-center gap-1">
            {d.regulations.length > 0 ? (
              d.regulations.slice(0, 3).map((r) => (
                <span
                  key={r}
                  className="rounded border border-hairline bg-veil-3/60 px-1.5 py-0.5 text-[10px] font-medium text-muted"
                >
                  {r}
                </span>
              ))
            ) : (
              <span className="text-[10.5px] text-faint">Unregulated</span>
            )}
          </div>
          {d.signed ? (
            <Badge tone="auralis">
              <BadgeCheck size={11} /> C2PA
            </Badge>
          ) : (
            <Badge tone="neutral">
              <FileWarning size={11} /> unsigned
            </Badge>
          )}
        </div>

        <div className="mt-3 flex items-center gap-1.5">
          <span className="h-1 w-1 rounded-full" style={{ background: TONE_HEX[SENSITIVITY_TONE[top]] }} />
          <span className="text-[10.5px] text-faint">
            max sensitivity · <span className="text-muted">{SENSITIVITY_LABEL[top]}</span>
          </span>
        </div>
      </Card>
    </Link>
  );
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wider text-faint">{label}</span>
      <span className="font-medium tabular-nums text-lumen">{value}</span>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <div className="mb-1.5 px-2.5 text-[10.5px] font-semibold uppercase tracking-wider text-faint">{title}</div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function Chip({ children, onClear }: { children: React.ReactNode; onClear: () => void }) {
  return (
    <button
      onClick={onClear}
      className="inline-flex items-center gap-1.5 rounded-full border border-auralis/30 bg-auralis/10 px-2.5 py-0.5 text-[11px] font-medium text-auralis transition-colors hover:bg-auralis/20"
    >
      {children}
      <X size={11} />
    </button>
  );
}
