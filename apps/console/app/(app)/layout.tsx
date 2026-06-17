import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { Shell } from "@/components/app-shell/shell";

/**
 * Authenticated application shell. The middleware already gates access; this
 * layout re-verifies server-side (defense in depth) and hands the resolved user
 * to the shell so the topbar reflects the real principal + RBAC role.
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const claims = await verifySession(token);
  if (!claims) redirect("/login");

  const user = {
    subject: claims.subject,
    displayName: claims.displayName,
    roles: claims.roles,
    jurisdiction: claims.jurisdiction,
    isSuperAdmin: claims.isSuperAdmin,
  };
  return <Shell user={user}>{children}</Shell>;
}
