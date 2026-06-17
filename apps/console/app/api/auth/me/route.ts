import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";

export const runtime = "nodejs";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const claims = await verifySession(token);
  if (!claims) return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  const { iat: _iat, exp: _exp, ...user } = claims;
  void _iat;
  void _exp;
  return NextResponse.json({ user });
}
