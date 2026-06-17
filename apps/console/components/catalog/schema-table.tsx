import { ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import type { Field } from "@/lib/types";
import { SENSITIVITY_LABEL, SENSITIVITY_TONE } from "./tokens";

/**
 * Dataset schema renderer. One row per field with its physical type, governance
 * classification (sensitivity badge + PII flag) and the semantic type it maps to
 * in the domain ontology — the bridge between raw columns and shared meaning.
 */
export function SchemaTable({ fields }: { fields: Field[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-hairline">
      <table className="w-full text-[12.5px]">
        <thead>
          <tr className="border-b border-hairline bg-veil-2/60 text-left text-[11px] uppercase tracking-wider text-faint">
            <th className="px-3 py-2 font-medium">Field</th>
            <th className="px-3 py-2 font-medium">Type</th>
            <th className="px-3 py-2 font-medium">Sensitivity</th>
            <th className="px-3 py-2 font-medium">PII</th>
            <th className="px-3 py-2 font-medium">Semantic type</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f) => (
            <tr key={f.name} className="border-b border-hairline/60 last:border-0 align-top hover:bg-veil-2/40">
              <td className="px-3 py-2.5">
                <div className="font-mono text-[12px] font-medium text-lumen">{f.name}</div>
                {f.description && <div className="mt-0.5 text-[11px] text-faint">{f.description}</div>}
              </td>
              <td className="px-3 py-2.5">
                <span className="rounded border border-hairline bg-veil-3/60 px-1.5 py-0.5 font-mono text-[11px] text-muted">
                  {f.type}
                </span>
              </td>
              <td className="px-3 py-2.5">
                <Badge tone={SENSITIVITY_TONE[f.sensitivity]}>{SENSITIVITY_LABEL[f.sensitivity]}</Badge>
              </td>
              <td className="px-3 py-2.5">
                {f.pii ? (
                  <span className="inline-flex items-center gap-1 text-[11.5px] font-medium text-crimson">
                    <ShieldAlert size={12} /> Yes
                  </span>
                ) : (
                  <span className="text-[11.5px] text-faint">—</span>
                )}
              </td>
              <td className="px-3 py-2.5">
                {f.semanticType ? (
                  <span className="font-mono text-[11.5px] text-auralis">{f.semanticType}</span>
                ) : (
                  <span className="text-faint">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
