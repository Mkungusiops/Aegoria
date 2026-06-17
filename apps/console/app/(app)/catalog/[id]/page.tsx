import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BadgeCheck,
  Boxes,
  Clock,
  Database,
  FileWarning,
  GitBranch,
  Globe2,
  MapPin,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  Table2,
  TerminalSquare,
} from "lucide-react";
import { Badge, Button, Card, Divider, KeyValue, Panel, ProgressBar, SectionHeader, Stat } from "@/components/ui/primitives";
import { FairBreakdown, fairScore } from "@/components/catalog/fair";
import { SchemaTable } from "@/components/catalog/schema-table";
import { MODALITY_LABEL, MODALITY_TONE, domainTone, qualityTone } from "@/components/catalog/tokens";
import { getDataset, fmtBytes, fmtNum } from "@/lib/data";

export default async function DatasetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const datasetId = decodeURIComponent(id);
  const d = await getDataset(datasetId);
  if (!d) notFound();

  const fair = fairScore(d.fair);
  const updated = new Date(d.updatedAt);
  const piiFields = d.fields.filter((f) => f.pii);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/catalog"
          className="mb-4 inline-flex items-center gap-1.5 text-[12.5px] text-muted transition-colors hover:text-auralis"
        >
          <ArrowLeft size={14} /> Data Catalog
        </Link>
        <PageHead dataset={d} />
      </div>

      {/* Headline metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Rows" value={fmtNum(d.rows)} unit={fmtBytes(d.bytes)} hint="indexed" />
            <Database size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="FAIR score" value={`${fair}`} unit="/ 4" tone="verdant" hint="principles met" />
            <Boxes size={18} className="text-verdant/70" />
          </div>
          <FairAxisStrip fair={d.fair} className="mt-3" />
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Quality" value={d.qualityScore.toFixed(2)} tone={qualityTone(d.qualityScore)} hint="passing rules" />
            <ShieldCheck size={18} className="text-verdant/70" />
          </div>
          <ProgressBar value={d.qualityScore * 100} tone={qualityTone(d.qualityScore)} className="mt-3.5" />
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="PII fields"
              value={`${d.piiFields}`}
              tone={d.piiFields > 0 ? "crimson" : "verdant"}
              hint={d.piiFields > 0 ? "masked off-org" : "no personal data"}
            />
            <ShieldAlert size={18} className="text-crimson/70" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Schema */}
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Schema"
            subtitle="Physical columns mapped to governance classifications and the shared domain ontology."
            icon={<Table2 size={16} />}
            action={<Badge tone="neutral">{d.fields.length} fields</Badge>}
          />
          <div className="mt-5">
            <SchemaTable fields={d.fields} />
          </div>
          {piiFields.length > 0 && (
            <div className="mt-4 flex items-start gap-2.5 rounded-md border border-crimson/25 bg-crimson/[0.06] px-3.5 py-3">
              <ShieldAlert size={15} className="mt-0.5 shrink-0 text-crimson" />
              <p className="text-[12px] leading-relaxed text-muted">
                <span className="font-medium text-lumen">{piiFields.length} personal-data field(s)</span> —{" "}
                <span className="font-mono text-[11.5px] text-crimson">
                  {piiFields.map((f) => f.name).join(", ")}
                </span>{" "}
                — are masked or differentially-private for any principal outside the owning organisation, enforced at query
                time by the governance service.
              </p>
            </div>
          )}
        </Card>

        {/* Trust column */}
        <div className="space-y-4">
          <Card>
            <SectionHeader title="FAIR breakdown" subtitle="Per-principle conformance." icon={<Boxes size={16} />} />
            <div className="mt-4">
              <FairBreakdown fair={d.fair} />
            </div>
          </Card>

          <Card>
            <SectionHeader title="Provenance" subtitle="Content authenticity & signing." icon={<ShieldCheck size={16} />} />
            <div className="mt-4">
              {d.signed ? (
                <div className="flex items-start gap-3 rounded-md border border-auralis/25 bg-auralis/[0.06] px-3.5 py-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-auralis/15 text-auralis">
                    <BadgeCheck size={18} />
                  </span>
                  <div>
                    <div className="text-[13px] font-medium text-lumen">C2PA manifest attached</div>
                    <div className="mt-0.5 text-[11.5px] leading-relaxed text-muted">
                      Cryptographically signed (ed25519). Every downstream product inherits a verifiable provenance chain.
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3 rounded-md border border-hairline bg-veil-2/50 px-3.5 py-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-veil-3 text-faint">
                    <FileWarning size={18} />
                  </span>
                  <div>
                    <div className="text-[13px] font-medium text-lumen">Unsigned source</div>
                    <div className="mt-0.5 text-[11.5px] leading-relaxed text-muted">
                      No C2PA manifest yet. Sign on next ingest to establish a verifiable provenance chain.
                    </div>
                  </div>
                </div>
              )}
            </div>
            <Divider className="my-4" />
            <KeyValue
              items={[
                { k: "Owner", v: d.owner },
                {
                  k: "Updated",
                  v: (
                    <span className="inline-flex items-center gap-1">
                      <Clock size={11} className="text-faint" />
                      {updated.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </span>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      </div>

      {/* License + jurisdiction + residency */}
      <Card>
        <SectionHeader
          title="License, jurisdiction & data residency"
          subtitle="The legal and regulatory envelope the engine enforces for every access."
          icon={<ScrollText size={16} />}
        />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Panel className="p-4">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
              <ScrollText size={13} /> License
            </div>
            <div className="mt-2 font-display text-[16px] font-semibold text-lumen">{d.license}</div>
            <div className="mt-1 text-[11.5px] text-muted">
              {d.license.startsWith("CC") || d.license.startsWith("ODbL")
                ? "Open license — attribution required."
                : "Restricted — contractual access only."}
            </div>
          </Panel>
          <Panel className="p-4">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
              <Globe2 size={13} /> Jurisdiction
            </div>
            <div className="mt-2 font-display text-[16px] font-semibold text-lumen">{d.jurisdiction}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {d.regulations.length > 0 ? (
                d.regulations.map((r) => (
                  <span
                    key={r}
                    className="rounded border border-hairline bg-veil-3/60 px-1.5 py-0.5 text-[10.5px] font-medium text-muted"
                  >
                    {r}
                  </span>
                ))
              ) : (
                <span className="text-[11.5px] text-faint">No specific regulations</span>
              )}
            </div>
          </Panel>
          <Panel className="p-4">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
              <MapPin size={13} /> Residency
            </div>
            <div className="mt-2 font-display text-[16px] font-semibold text-lumen">
              {d.residencyRequired ? `Pinned · ${d.jurisdiction}` : "Unconstrained"}
            </div>
            <div className="mt-1 text-[11.5px] text-muted">
              {d.residencyRequired
                ? "Compute is placed only in compliant regions; cross-border processing is denied."
                : "May be processed in the greenest capable region worldwide."}
            </div>
          </Panel>
        </div>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {d.tags.map((t) => (
            <span key={t} className="rounded-full border border-hairline bg-veil-2/50 px-2.5 py-0.5 text-[11px] text-muted">
              #{t}
            </span>
          ))}
        </div>
      </Card>

      {/* Lineage teaser + actions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Lineage"
            subtitle="This dataset participates in a verifiable upstream/downstream chain — see the full graph."
            icon={<GitBranch size={16} />}
            action={
              <Link href="/lineage" className="text-[12px] text-auralis hover:underline">
                Open lineage →
              </Link>
            }
          />
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-hairline bg-veil-2/40 px-4 py-4 text-[12.5px]">
            <LineageChip tone="solar">Source</LineageChip>
            <span className="text-faint">→</span>
            <LineageChip tone="auralis" emphasis>
              {d.name}
            </LineageChip>
            <span className="text-faint">→</span>
            <LineageChip tone="pulse">Model</LineageChip>
            <span className="text-faint">→</span>
            <LineageChip tone="verdant">Data product</LineageChip>
          </div>
        </Card>

        <Card>
          <SectionHeader title="Actions" subtitle="Governed, sample-ready." icon={<TerminalSquare size={16} />} />
          <div className="mt-4 space-y-2.5">
            <Link href="/query" className="block">
              <Button variant="primary" className="w-full justify-center">
                <TerminalSquare size={15} /> Query in Studio
              </Button>
            </Link>
            <Link href="/lineage" className="block">
              <Button variant="default" className="w-full justify-center">
                <GitBranch size={15} /> View lineage
              </Button>
            </Link>
            <Link href="/trust" className="block">
              <Button variant="default" className="w-full justify-center">
                <ShieldCheck size={15} /> Privacy & policies
              </Button>
            </Link>
          </div>
          <p className="mt-4 text-[11px] leading-relaxed text-faint">
            All access flows through the engine: authorization, carbon-aware placement and privacy obligations are applied
            before a single row is returned.
          </p>
        </Card>
      </div>
    </div>
  );
}

function PageHead({
  dataset: d,
}: {
  dataset: NonNullable<Awaited<ReturnType<typeof getDataset>>>;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-hairline pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="animate-fade-up">
        <div className="mb-2 flex items-center gap-1.5">
          <Badge tone={domainTone(d.domain)}>{d.domain}</Badge>
          <Badge tone={MODALITY_TONE[d.modality]}>{MODALITY_LABEL[d.modality]}</Badge>
          {d.signed ? (
            <Badge tone="auralis">
              <BadgeCheck size={11} /> C2PA signed
            </Badge>
          ) : (
            <Badge tone="neutral">
              <FileWarning size={11} /> unsigned
            </Badge>
          )}
        </div>
        <h1 className="font-display text-[28px] font-semibold leading-tight tracking-tight text-lumen text-balance">
          {d.title}
        </h1>
        <p className="mt-1 font-mono text-[12px] text-faint">{d.id}</p>
        <p className="mt-2 max-w-2xl text-[13.5px] leading-relaxed text-muted">{d.description}</p>
      </div>
    </div>
  );
}

function FairAxisStrip({ fair, className }: { fair: import("@/lib/types").FairFlags; className?: string }) {
  const axes: { key: keyof import("@/lib/types").FairFlags; letter: string }[] = [
    { key: "findable", letter: "F" },
    { key: "accessible", letter: "A" },
    { key: "interoperable", letter: "I" },
    { key: "reusable", letter: "R" },
  ];
  return (
    <div className={`flex gap-1.5 ${className ?? ""}`}>
      {axes.map((a) => (
        <span
          key={a.key}
          className={`grid h-6 flex-1 place-items-center rounded text-[11px] font-semibold ${
            fair[a.key] ? "bg-verdant/15 text-verdant" : "bg-veil-3 text-faint"
          }`}
        >
          {a.letter}
        </span>
      ))}
    </div>
  );
}

function LineageChip({
  children,
  tone,
  emphasis = false,
}: {
  children: React.ReactNode;
  tone: "auralis" | "pulse" | "verdant" | "solar";
  emphasis?: boolean;
}) {
  const tones = {
    auralis: "border-auralis/40 bg-auralis/10 text-auralis",
    pulse: "border-pulse/30 bg-pulse/10 text-[#b3a4ff]",
    verdant: "border-verdant/30 bg-verdant/10 text-verdant",
    solar: "border-solar/30 bg-solar/10 text-solar",
  }[tone];
  return (
    <span
      className={`rounded-md border px-2.5 py-1 font-medium ${tones} ${emphasis ? "font-mono shadow-[0_0_0_1px_rgba(22,224,196,0.15)]" : ""}`}
    >
      {children}
    </span>
  );
}
