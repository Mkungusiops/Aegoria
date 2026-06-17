import { Search, Leaf, Command } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { UserMenu } from "./user-menu";
import type { SessionUser } from "@/lib/auth/session";

export function Topbar({
  user,
  region = "eu-north",
  carbon = 28,
}: {
  user?: SessionUser;
  region?: string;
  carbon?: number;
}) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-hairline bg-veil/70 px-5 backdrop-blur-xl sm:px-8">
      <div className="relative w-full max-w-md">
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
        <input
          type="text"
          placeholder="Search datasets, entities, lineage, policies…"
          className="h-9 w-full rounded-md border border-hairline bg-veil-1 pl-9 pr-16 text-[13px] text-lumen placeholder:text-faint focus:border-auralis/40 focus:outline-none focus:ring-2 focus:ring-auralis/20"
        />
        <kbd className="absolute right-2.5 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-hairline bg-veil-2 px-1.5 py-0.5 text-[10px] text-faint sm:flex">
          <Command size={10} /> K
        </kbd>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <Badge tone="verdant" dot>
          <Leaf size={11} className="mr-0.5" /> {region} · {carbon} gCO₂/kWh
        </Badge>
        <ThemeToggle />
        {user && <UserMenu user={user} />}
      </div>
    </header>
  );
}
