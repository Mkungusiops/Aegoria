"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { LogOut, ShieldCheck, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/primitives";
import type { SessionUser } from "@/lib/auth/session";

function roleLabel(user: SessionUser): { label: string; tone: "auralis" | "pulse" | "verdant" | "neutral" } {
  if (user.isSuperAdmin) return { label: "Super Admin", tone: "auralis" };
  if (user.roles.includes("steward") || user.roles.includes("admin")) return { label: "Steward", tone: "pulse" };
  if (user.roles.includes("analyst")) return { label: "Analyst", tone: "verdant" };
  return { label: "Viewer", tone: "neutral" };
}

function initials(name: string): string {
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

export function UserMenu({ user }: { user: SessionUser }) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const role = roleLabel(user);

  React.useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 rounded-md px-1.5 py-1 transition-colors hover:bg-veil-2"
      >
        <div className="hidden text-right sm:block">
          <div className="text-[12px] font-medium leading-tight text-lumen">{user.displayName}</div>
          <div className="text-[10.5px] leading-tight text-faint">{role.label} · {user.jurisdiction}</div>
        </div>
        <div
          className={cn(
            "grid h-9 w-9 place-items-center rounded-full text-[13px] font-semibold text-ink",
            user.isSuperAdmin ? "bg-auralis-gradient" : "bg-veil-3 text-lumen",
          )}
        >
          {initials(user.displayName)}
        </div>
        <ChevronDown size={14} className="hidden text-faint sm:block" />
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-50 w-60 animate-fade-up rounded-lg border border-hairline bg-veil-1 p-2 shadow-panel">
          <div className="flex items-center gap-3 rounded-md px-2.5 py-2.5">
            <div
              className={cn(
                "grid h-9 w-9 place-items-center rounded-full text-[13px] font-semibold text-ink",
                user.isSuperAdmin ? "bg-auralis-gradient" : "bg-veil-3 text-lumen",
              )}
            >
              {initials(user.displayName)}
            </div>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-medium text-lumen">{user.displayName}</div>
              <div className="truncate text-[11px] text-faint">@{user.subject}</div>
            </div>
          </div>
          <div className="px-2.5 pb-2">
            <Badge tone={role.tone} dot>
              {user.isSuperAdmin && <ShieldCheck size={11} className="mr-0.5" />}
              {role.label}
            </Badge>
          </div>
          <div className="mb-1.5 px-2.5">
            <div className="text-[10px] uppercase tracking-wider text-faint">Roles</div>
            <div className="mt-1 flex flex-wrap gap-1">
              {user.roles.map((r) => (
                <span key={r} className="rounded bg-veil-2 px-1.5 py-0.5 font-mono text-[10px] text-muted">{r}</span>
              ))}
            </div>
          </div>
          <div className="my-1 h-px bg-hairline" />
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-[13px] text-muted transition-colors hover:bg-veil-2 hover:text-crimson"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
