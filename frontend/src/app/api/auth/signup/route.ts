import { NextResponse } from "next/server";

import { backendFetch } from "@/lib/auth/backend";
import { setRefreshCookie } from "@/lib/auth/cookies";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface SignupBody {
  organization_name: string;
  organization_slug: string;
  email: string;
  password: string;
  full_name: string;
}

function isSignupBody(value: unknown): value is SignupBody {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.organization_name === "string" &&
    typeof v.organization_slug === "string" &&
    typeof v.email === "string" &&
    typeof v.password === "string" &&
    typeof v.full_name === "string"
  );
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!isSignupBody(body)) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  const created = await backendFetch<unknown>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!created.ok) {
    return NextResponse.json(
      { error: created.error ?? "Signup failed" },
      { status: created.status }
    );
  }

  const tokens = await backendFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: body.email, password: body.password }),
  });
  if (!tokens.ok || !tokens.data) {
    return NextResponse.json(
      { error: tokens.error ?? "Auto-login failed" },
      { status: tokens.status }
    );
  }

  const res = NextResponse.json({
    access_token: tokens.data.access_token,
    user: created.data,
  });
  setRefreshCookie(res, tokens.data.refresh_token, req);
  return res;
}
