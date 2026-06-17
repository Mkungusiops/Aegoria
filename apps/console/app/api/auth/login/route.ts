import { NextResponse } from "next/server";
import { authenticate } from "@/lib/auth/users";
import { SESSION_COOKIE, SESSION_MAX_AGE, signSession } from "@/lib/auth/session";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const user = authenticate(String(body.username ?? ""), String(body.password ?? ""));
  if (!user) {
    return NextResponse.json({ error: "Invalid username or password" }, { status: 401 });
  }
  const token = await signSession(user);
  const res = NextResponse.json({ user });
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    // Demo runs over http://localhost; enable `secure` behind TLS in production.
    secure: false,
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return res;
}
