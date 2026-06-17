import {
  Boxes,
  Database,
  Network,
  ShieldCheck,
  BrainCircuit,
  CheckCircle2,
  Download,
  FileCode2,
} from "lucide-react";
import type { DomainPack } from "@/lib/types";
import { Badge, Button, Divider } from "@/components/ui/primitives";
import { MODALITY_META } from "@/components/pipelines/pipeline-utils";

/** One countable manifest artifact rendered as a compact metric. */
function ArtifactStat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-md border border-hairline bg-veil-2/40 py-2.5">
      <span className="text-faint">{icon}</span>
      <span className="font-display text-[16px] font-semibold tabular-nums text-lumen">{value}</span>
      <span className="text-[10px] uppercase tracking-wider text-faint">{label}</span>
    </div>
  );
}

/**
 * A domain-pack card. Installed packs read as "active" with an Inspect action;
 * marketplace packs lead with Install. Every card foregrounds the declarative
 * artifact counts (datasets / ontology / rules / models / policies) to make the
 * "onboard a market by writing a manifest" story concrete.
 */
export function PackCard({ pack }: { pack: DomainPack }) {
  const installed = pack.status === "active";
  const [sector, focus] = pack.name.split(" · ");

  return (
    <div
      className={`surface group relative flex flex-col p-5 transition-shadow duration-300 ${
        installed ? "shadow-glow" : "hover:border-auralis/30"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={`grid h-10 w-10 shrink-0 place-items-center rounded-md border bg-veil-2 ${
              installed ? "border-auralis/40 text-auralis" : "border-hairline text-muted"
            }`}
          >
            <Boxes size={18} />
          </span>
          <div className="min-w-0">
            <div className="text-[14px] font-semibold leading-tight text-lumen">{sector}</div>
            <div className="mt-0.5 truncate text-[11.5px] text-muted">{focus}</div>
          </div>
        </div>
        {installed ? (
          <Badge tone={pack.color} dot>
            active
          </Badge>
        ) : (
          <Badge tone="neutral">marketplace</Badge>
        )}
      </div>

      {/* Description */}
      <p className="mt-3 text-[12.5px] leading-relaxed text-muted">{pack.description}</p>

      {/* Modalities */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {pack.modalities.map((m) => (
          <Badge key={m} tone={MODALITY_META[m].tone}>
            {MODALITY_META[m].label}
          </Badge>
        ))}
      </div>

      {/* Artifact counts — the declarative payload */}
      <div className="mt-4 grid grid-cols-5 gap-2">
        <ArtifactStat icon={<Database size={14} />} value={pack.datasets} label="data" />
        <ArtifactStat icon={<Network size={14} />} value={pack.ontologyTerms} label="terms" />
        <ArtifactStat icon={<CheckCircle2 size={14} />} value={pack.qualityRules} label="rules" />
        <ArtifactStat icon={<BrainCircuit size={14} />} value={pack.models} label="models" />
        <ArtifactStat icon={<ShieldCheck size={14} />} value={pack.policies} label="policy" />
      </div>

      <Divider className="my-4" />

      {/* Meta + actions */}
      <div className="mt-auto">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11.5px]">
          <div className="flex flex-col">
            <span className="text-faint">Version</span>
            <span className="font-mono text-[11.5px] text-lumen">v{pack.version}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-faint">Core compat</span>
            <span className="font-mono text-[11.5px] text-auralis">{pack.coreCompat}</span>
          </div>
          <div className="col-span-2 flex flex-col">
            <span className="text-faint">Maintainer</span>
            <span className="text-lumen">{pack.maintainer}</span>
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          {installed ? (
            <>
              <Button variant="default" className="flex-1 justify-center" disabled>
                <FileCode2 size={14} /> Inspect manifest
              </Button>
              <Button variant="ghost" disabled>
                Configured
              </Button>
            </>
          ) : (
            <>
              <Button variant="primary" className="flex-1 justify-center" disabled>
                <Download size={14} /> Install
              </Button>
              <Button variant="default" disabled>
                <FileCode2 size={14} /> Manifest
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
