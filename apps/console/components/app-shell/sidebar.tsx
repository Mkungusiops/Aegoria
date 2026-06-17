"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { Wordmark } from "@/components/ui/logo";
import { NAV, NAV_GROUPS } from "./nav";

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-[252px] shrink-0 flex-col border-r border-hairline bg-veil-1/60 backdrop-blur-xl lg:flex">
      <div className="flex h-16 items-center border-b border-hairline px-5">
        <Link href="/" aria-label="Aegoria home">
          <Wordmark />
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group} className="mb-5">
            <div className="px-3 pb-2 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-faint">{group}</div>
            <ul className="space-y-0.5">
              {NAV.filter((n) => n.group === group).map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "group relative flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-all",
                        active ? "bg-auralis/10 text-lumen" : "text-muted hover:bg-veil-2 hover:text-lumen",
                      )}
                    >
                      {active && <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-auralis" />}
                      <Icon size={16} className={cn("transition-colors", active ? "text-auralis" : "text-faint group-hover:text-muted")} />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-hairline p-3">
        <div className="surface-2 flex items-center gap-3 p-3">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-verdant" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-verdant" />
          </span>
          <div className="min-w-0">
            <div className="truncate text-[12px] font-medium text-lumen">Core engine v0.1.0</div>
            <div className="truncate text-[11px] text-faint">lite · 4 domains live</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
