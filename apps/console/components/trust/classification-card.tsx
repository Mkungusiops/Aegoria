import { EyeOff, Eye, Fingerprint } from "lucide-react";
import { Badge, Panel } from "@/components/ui/primitives";
import type { Dataset } from "@/lib/types";
import { SENSITIVITY_META } from "./sensitivity";

/**
 * Per-dataset classification card. Surfaces every field, its detected
 * sensitivity, and whether the trust fabric masks it before results leave
 * the perimeter. A masked field is the default for anything regulated —
 * exposure is the exception and is visually quieter (verdant), masking is
 * loud (crimson lock) so reviewers can scan for accidental exposure.
 */
export function ClassificationCard({ dataset }: { dataset: Dataset }) {
  const regulated = dataset.fields.filter((f) => SENSITIVITY_META[f.sensitivity].regulated);
  const maskedCount = dataset.fields.filter((f) => SENSITIVITY_META[f.sensitivity].maskedByDefault).length;

  return (
    <Panel className="flex flex-col p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[13px] font-medium text-lumen">{dataset.title}</div>
          <div className="mt-0.5 truncate font-mono text-[10.5px] text-faint">{dataset.name}</div>
        </div>
        {dataset.piiFields > 0 ? (
          <Badge tone="crimson">
            <Fingerprint size={11} /> {dataset.piiFields} PII
          </Badge>
        ) : (
          <Badge tone="verdant">no PII</Badge>
        )}
      </div>

      <div className="mt-3 flex items-center gap-3 text-[11px] text-faint">
        <span>{dataset.fields.length} fields</span>
        <span className="text-hairline">·</span>
        <span className="text-crimson/80">{maskedCount} masked by default</span>
        <span className="text-hairline">·</span>
        <span className="text-verdant/80">{dataset.fields.length - maskedCount} exposed</span>
      </div>

      <ul className="mt-3 space-y-1.5">
        {dataset.fields.map((f) => {
          const meta = SENSITIVITY_META[f.sensitivity];
          return (
            <li
              key={f.name}
              className="flex items-center justify-between gap-2 rounded-md border border-hairline/70 bg-veil/40 px-2.5 py-1.5"
            >
              <div className="flex min-w-0 items-center gap-2">
                {meta.maskedByDefault ? (
                  <EyeOff size={13} className="shrink-0 text-crimson/80" />
                ) : (
                  <Eye size={13} className="shrink-0 text-verdant/70" />
                )}
                <span className="truncate font-mono text-[11.5px] text-lumen">{f.name}</span>
                <span className="truncate text-[10.5px] text-faint">{f.type}</span>
              </div>
              <Badge tone={meta.tone}>{meta.label}</Badge>
            </li>
          );
        })}
      </ul>

      {regulated.length > 0 && (
        <div className="mt-3 rounded-md border border-crimson/20 bg-crimson/5 px-2.5 py-1.5 text-[10.5px] leading-relaxed text-muted">
          <span className="font-medium text-crimson/90">Auto-protected:</span>{" "}
          {regulated.map((f) => f.name).join(", ")} masked / tokenized before egress.
        </div>
      )}
    </Panel>
  );
}
