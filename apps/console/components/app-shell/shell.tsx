import * as React from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import type { SessionUser } from "@/lib/auth/session";

export function Shell({ children, user }: { children: React.ReactNode; user?: SessionUser }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar roles={user?.roles} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} />
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-7 sm:px-8 sm:py-9">{children}</main>
      </div>
    </div>
  );
}
