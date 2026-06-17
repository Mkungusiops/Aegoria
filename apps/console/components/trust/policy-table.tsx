import { Ban, Check } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import type { AccessPolicy } from "@/lib/types";

/**
 * ABAC/RBAC access-policy table. Allow rules read calmly; DENY rules (e.g.
 * data-residency fences) are rendered in crimson with a distinct left rail so
 * a reviewer instantly sees the hard boundaries the engine enforces before any
 * compute is placed.
 */
export function PolicyTable({ policies }: { policies: AccessPolicy[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-hairline">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-hairline bg-veil-2/60 text-left text-[10.5px] uppercase tracking-wider text-faint">
            <th className="px-3 py-2 font-medium">Effect</th>
            <th className="px-3 py-2 font-medium">Policy</th>
            <th className="px-3 py-2 font-medium">Roles</th>
            <th className="px-3 py-2 font-medium">Actions</th>
            <th className="px-3 py-2 font-medium">Scope</th>
            <th className="px-3 py-2 font-medium">Condition</th>
            <th className="px-3 py-2 font-medium">Obligations</th>
          </tr>
        </thead>
        <tbody>
          {policies.map((p) => {
            const deny = p.effect === "deny";
            return (
              <tr
                key={p.id}
                className={
                  "border-b border-hairline/60 align-top last:border-0 " +
                  (deny ? "bg-crimson/[0.04] hover:bg-crimson/[0.07]" : "hover:bg-veil-2/40")
                }
              >
                <td className="px-3 py-2.5">
                  <span
                    className={
                      "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10.5px] font-semibold uppercase tracking-wide " +
                      (deny
                        ? "border-crimson/40 bg-crimson/10 text-crimson"
                        : "border-verdant/30 bg-verdant/10 text-verdant")
                    }
                  >
                    {deny ? <Ban size={11} /> : <Check size={11} />}
                    {p.effect}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="font-mono text-[11px] text-lumen">{p.id}</div>
                  <div className="mt-0.5 max-w-[220px] text-[10.5px] leading-snug text-faint">{p.description}</div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {p.roles.map((r) => (
                      <span key={r} className="rounded bg-veil-3 px-1.5 py-0.5 font-mono text-[10px] text-muted">
                        {r}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {p.actions.map((a) => (
                      <span key={a} className="text-[10.5px] text-muted">
                        {a}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-col gap-0.5">
                    {p.datasets.map((d) => (
                      <span key={d} className="font-mono text-[10px] text-ion/90">
                        {d}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  {p.condition ? (
                    <code
                      className={
                        "block max-w-[180px] rounded px-1.5 py-1 font-mono text-[10px] leading-snug " +
                        (deny ? "bg-crimson/10 text-crimson/90" : "bg-veil-3 text-muted")
                      }
                    >
                      {p.condition}
                    </code>
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-col gap-1">
                    {p.obligations.length === 0 && <span className="text-faint">—</span>}
                    {p.obligations.map((o) => (
                      <Badge key={o} tone={deny ? "crimson" : "pulse"}>
                        {o}
                      </Badge>
                    ))}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
