import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendFetch } from "@/lib/auth/backend";
import {
  REFRESH_COOKIE_NAME,
  clearRefreshCookie,
  setRefreshCookie,
} from "@/lib/auth/cookies";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function POST() {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE_NAME)?.value;
  if (!refreshToken) {
    return NextResponse.json({ error: "No refresh token" }, { status: 401 });
  }

  const tokens = await backendFetch<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!tokens.ok || !tokens.data) {
    const res = NextResponse.json(
      { error: tokens.error ?? "Refresh failed" },
      { status: tokens.status }
    );
    clearRefreshCookie(res);
    return res;
  }

  const me = await backendFetch<unknown>("/users/me", {
    headers: { Authorization: `Bearer ${tokens.data.access_token}` },
  });
  if (!me.ok) {
    const res = NextResponse.json(
      { error: me.error ?? "Could not load user" },
      { status: me.status }
    );
    clearRefreshCookie(res);
    return res;
  }

  const res = NextResponse.json({
    access_token: tokens.data.access_token,
    user: me.data,
  });
  setRefreshCookie(res, tokens.data.refresh_token);
  return res;
}
