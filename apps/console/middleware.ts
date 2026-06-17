import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";

/**
 * Auth gate. Every route requires a valid signed session except the login page,
 * the auth API, Next internals and static assets. Unauthenticated requests are
 * redirected to /login (preserving the intended destination).
 */
export async function middleware(req: NextRequest) {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  const claims = await verifySession(token);
  if (claims) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("from", req.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.svg|.*\\.svg$).*)"],
};
