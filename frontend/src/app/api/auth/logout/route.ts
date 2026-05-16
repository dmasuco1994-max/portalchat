import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendFetch } from "@/lib/auth/backend";
import { REFRESH_COOKIE_NAME, clearRefreshCookie } from "@/lib/auth/cookies";

export async function POST(req: Request) {
  const auth = req.headers.get("authorization");
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE_NAME)?.value;

  if (refreshToken && auth) {
    // Best-effort: backend revokes the refresh token. If the access token is
    // already expired we still clear the cookie locally.
    await backendFetch("/auth/logout", {
      method: "POST",
      headers: { Authorization: auth },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  const res = NextResponse.json({ ok: true });
  clearRefreshCookie(res);
  return res;
}
