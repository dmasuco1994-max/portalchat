import { NextResponse } from "next/server";

import { backendFetch } from "@/lib/auth/backend";
import { setRefreshCookie } from "@/lib/auth/cookies";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.email !== "string" || typeof body.password !== "string") {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  const tokens = await backendFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: body.email, password: body.password }),
  });

  if (!tokens.ok || !tokens.data) {
    return NextResponse.json(
      { error: tokens.error ?? "Login failed" },
      { status: tokens.status }
    );
  }

  const me = await backendFetch<unknown>("/users/me", {
    headers: { Authorization: `Bearer ${tokens.data.access_token}` },
  });

  if (!me.ok) {
    return NextResponse.json(
      { error: me.error ?? "Could not load user" },
      { status: me.status }
    );
  }

  const res = NextResponse.json({
    access_token: tokens.data.access_token,
    user: me.data,
  });
  setRefreshCookie(res, tokens.data.refresh_token, req);
  return res;
}
