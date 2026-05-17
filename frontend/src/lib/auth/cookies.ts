import type { NextResponse } from "next/server";

export const REFRESH_COOKIE_NAME = "wp_refresh";

const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

// HTTPS is detected from the actual request, not NODE_ENV. Marking a cookie
// Secure over HTTP makes the browser silently drop it — that breaks deploys
// on internal LAN VMs without TLS. x-forwarded-proto wins so reverse proxies
// (nginx, traefik) terminating TLS still produce Secure cookies upstream.
function isHttps(req: Request): boolean {
  const forwarded = req.headers.get("x-forwarded-proto");
  if (forwarded) return forwarded.split(",")[0].trim() === "https";
  try {
    return new URL(req.url).protocol === "https:";
  } catch {
    return false;
  }
}

export function setRefreshCookie(
  res: NextResponse,
  refreshToken: string,
  req: Request
) {
  res.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: refreshToken,
    httpOnly: true,
    sameSite: "lax",
    secure: isHttps(req),
    path: "/",
    maxAge: SEVEN_DAYS_SECONDS,
  });
}

export function clearRefreshCookie(res: NextResponse, req: Request) {
  res.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: isHttps(req),
    path: "/",
    maxAge: 0,
  });
}
