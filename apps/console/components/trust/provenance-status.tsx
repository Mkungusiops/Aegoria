import { BadgeCheck, ShieldAlert, FileSignature } from "lucide-react";
import { Badge, Panel } from "@/components/ui/primitives";
import type { Dataset } from "@/lib/types";

/**
 * C2PA provenance / verification status. Every published dataset should carry
 * an Ed25519-signed content-provenance manifest (C2PA) so consumers can verify
 * origin and integrity. Unsigned datasets are flagged — they are the exception
 * the governance council is actively closing.
 */
export function ProvenanceStatus({ datasets }: { datasets: Dataset[] }) {
  const signed = datasets.filter((d) => d.signed);
  const coverage = datasets.length ? Math.round((signed.length / datasets.length) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 rounded-md border border-hairline bg-veil-2/50 px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <FileSignature size={16} className="text-auralis/80" />
          <div className="leading-tight">
            <div className="text-[12.5px] font-medium text-lumen">C2PA manifest coverage</div>
            <div className="text-[10.5px] text-faint">Ed25519 content credentials, verified on read</div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-display text-[20px] font-semibold tabular-nums text-lumen">{coverage}%</div>
          <div className="text-[10px] text-faint">
            {signed.length}/{datasets.length} signed
          </div>
        </div>
      </div>

      <ul className="space-y-1.5">
        {datasets.map((d) => (
          <li
            key={d.id}
            className="flex items-center justify-between gap-2 rounded-md border border-hairline/70 bg-veil/40 px-3 py-2"
          >
            <div className="flex min-w-0 items-center gap-2">
              {d.signed ? (
                <BadgeCheck size={14} className="shrink-0 text-verdant" />
              ) : (
                <ShieldAlert size={14} className="shrink-0 text-solar" />
              )}
              <span className="truncate text-[12px] text-lumen">{d.title}</span>
            </div>
            <Badge tone={d.signed ? "verdant" : "solar"}>{d.signed ? "verified" : "unsigned"}</Badge>
          </li>
        ))}
      </ul>

      <Panel className="p-3 text-[10.5px] leading-relaxed text-muted">
        Manifests bind lineage, license and quality attestations to a tamper-evident hash chain. Verification runs at
        query time — a broken or missing signature downgrades the result to <span className="text-solar">unverified</span>.
      </Panel>
    </div>
  );
}
