import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { LoginForm } from "./login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string }>;
}) {
  // Already authenticated? Skip the login screen.
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (await verifySession(token)) redirect("/");

  const { from } = await searchParams;
  const safeFrom = from && from.startsWith("/") && !from.startsWith("/login") ? from : "/";
  return <LoginForm from={safeFrom} />;
}
