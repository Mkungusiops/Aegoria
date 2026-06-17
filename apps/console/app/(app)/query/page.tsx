import { Leaf, MapPin, ShieldCheck, TerminalSquare } from "lucide-react";
import { Card, PageHeader, Stat } from "@/components/ui/primitives";
import { QueryStudio } from "@/components/query/query-studio";
import { buildExamples } from "@/components/query/examples";
import { getCarbon, getQueryRuns } from "@/lib/data";

export const metadata = {
  title: "Query Studio — Aegoria",
  description: "Run governed SQL with a verifiable carbon and privacy receipt.",
};

export default async function QueryStudioPage() {
  const [runs, carbon] = await Promise.all([getQueryRuns(), getCarbon()]);
  const examples = buildExamples(runs);

  const greenest = [...carbon].sort((a, b) => a.gco2PerKwh - b.gco2PerKwh)[0];
  const authorized = examples.filter((e) => e.status !== "denied").length;
  const dpQueries = examples.filter((e) => e.dpApplied).length;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Query Studio"
        title="Every query, governed end-to-end"
        description="Author SQL once. The engine authorizes the principal, places the workload in the greenest capable region, enforces differential privacy and masks protected columns — then returns rows alongside a verifiable governance receipt. The receipt is the product."
      />

      {/* Context strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Greenest region" value={greenest?.region ?? "—"} unit={`${greenest?.gco2PerKwh ?? 0} g`} tone="verdant" hint="auto-selected" />
            <MapPin size={18} className="text-verdant/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Renewable mix" value={`${Math.round((greenest?.renewableFraction ?? 0) * 100)}%`} tone="verdant" hint="at chosen region" />
            <Leaf size={18} className="text-verdant/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Authorized" value={`${authorized}`} unit={`/ ${examples.length}`} tone="auralis" hint="example queries" />
            <ShieldCheck size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="DP enforced" value={`${dpQueries}`} unit="ε-bounded" tone="pulse" hint="privacy applied" />
            <TerminalSquare size={18} className="text-pulse/70" />
          </div>
        </Card>
      </div>

      <QueryStudio examples={examples} />
    </div>
  );
}
