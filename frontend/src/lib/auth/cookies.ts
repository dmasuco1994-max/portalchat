import type { NextResponse } from "next/server";

export const REFRESH_COOKIE_NAME = "wp_refresh";

const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

export function setRefreshCookie(res: NextResponse, refreshToken: string) {
  res.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: refreshToken,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SEVEN_DAYS_SECONDS,
  });
}

export function clearRefreshCookie(res: NextResponse) {
  res.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
}
