import { BadgeCheck, Boxes, Database, Layers, ShieldAlert } from "lucide-react";
import { Card, PageHeader, Stat } from "@/components/ui/primitives";
import { CatalogBrowser } from "@/components/catalog/catalog-browser";
import { fairScore } from "@/components/catalog/fair";
import { getDatasets, fmtNum } from "@/lib/data";

export const metadata = {
  title: "Data Catalog — Aegoria",
  description: "FAIR catalog of every dataset across all onboarded domains.",
};

export default async function CatalogPage() {
  const datasets = await getDatasets();

  const domains = new Set(datasets.map((d) => d.domain)).size;
  const totalRows = datasets.reduce((n, d) => n + d.rows, 0);
  const signed = datasets.filter((d) => d.signed).length;
  const piiFields = datasets.reduce((n, d) => n + d.piiFields, 0);
  const fairAvg = datasets.length
    ? datasets.reduce((n, d) => n + fairScore(d.fair), 0) / datasets.length
    : 0;
  const qualityAvg = datasets.length
    ? datasets.reduce((n, d) => n + d.qualityScore, 0) / datasets.length
    : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Data Catalog"
        title="Every dataset, FAIR by construction"
        description="A single, market-agnostic catalog spanning climate, finance and beyond. Each dataset carries its FAIR posture, quality, jurisdiction, regulatory footprint and verifiable C2PA provenance — discoverable without ever leaving the trust boundary."
      />

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Datasets" value={`${datasets.length}`} unit={`/ ${domains} domains`} hint="cataloged" />
            <Database size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Rows indexed" value={fmtNum(totalRows)} tone="ion" hint="across catalog" />
            <Layers size={18} className="text-ion/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="FAIR · quality"
              value={fairAvg.toFixed(1)}
              unit={`/4 · ${qualityAvg.toFixed(2)}`}
              tone="verdant"
              hint="catalog average"
            />
            <Boxes size={18} className="text-verdant/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="C2PA signed"
              value={`${signed}`}
              unit={`/ ${datasets.length}`}
              tone="auralis"
              hint="verifiable provenance"
            />
            <BadgeCheck size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:240ms]">
          <div className="flex items-start justify-between">
            <Stat label="PII fields" value={`${piiFields}`} tone={piiFields > 0 ? "crimson" : "verdant"} hint="policy-governed" />
            <ShieldAlert size={18} className="text-crimson/70" />
          </div>
        </Card>
      </div>

      <CatalogBrowser datasets={datasets} />
    </div>
  );
}
