"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";

import { setOnAuthFail } from "@/lib/api/client";
import { setAccessToken } from "@/lib/api/token-store";
import type { User } from "@/lib/api/types";

type Status = "loading" | "authenticated" | "unauthenticated";

interface LoginInput {
  email: string;
  password: string;
}

interface SignupInput {
  organization_name: string;
  organization_slug: string;
  email: string;
  password: string;
  full_name: string;
}

interface AuthContextValue {
  status: Status;
  user: User | null;
  login: (input: LoginInput) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => Promise<void>;
  /** Replace the in-memory user (e.g. after editing the own profile). */
  setUser: (user: User) => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

const PUBLIC_PATHS = new Set(["/login", "/signup"]);

async function postJson<T>(path: string, body: unknown, token?: string | null): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body ?? {}),
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  return data as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = React.useState<Status>("loading");
  const [user, setUser] = React.useState<User | null>(null);
  const accessTokenRef = React.useRef<string | null>(null);

  const applySession = React.useCallback(
    (accessToken: string, nextUser: User) => {
      accessTokenRef.current = accessToken;
      setAccessToken(accessToken);
      setUser(nextUser);
      setStatus("authenticated");
    },
    []
  );

  const clearSession = React.useCallback(() => {
    accessTokenRef.current = null;
    setAccessToken(null);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  // Wire the API client's auth-fail callback exactly once.
  React.useEffect(() => {
    setOnAuthFail(() => {
      clearSession();
      router.replace("/login");
    });
    return () => setOnAuthFail(null);
  }, [clearSession, router]);

  // Silent refresh on mount — recovers the session from the httpOnly cookie.
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await postJson<{ access_token: string; user: User }>(
          "/api/auth/refresh",
          {}
        );
        if (cancelled) return;
        applySession(data.access_token, data.user);
      } catch {
        if (cancelled) return;
        clearSession();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applySession, clearSession]);

  // After the silent refresh resolves, send users to the right place.
  React.useEffect(() => {
    if (status === "loading") return;
    const onPublic = PUBLIC_PATHS.has(pathname);
    if (status === "authenticated" && onPublic) {
      router.replace("/");
    } else if (status === "unauthenticated" && !onPublic) {
      router.replace("/login");
    }
  }, [status, pathname, router]);

  const login = React.useCallback<AuthContextValue["login"]>(
    async (input) => {
      const data = await postJson<{ access_token: string; user: User }>(
        "/api/auth/login",
        input
      );
      applySession(data.access_token, data.user);
    },
    [applySession]
  );

  const signup = React.useCallback<AuthContextValue["signup"]>(
    async (input) => {
      const data = await postJson<{ access_token: string; user: User }>(
        "/api/auth/signup",
        input
      );
      applySession(data.access_token, data.user);
    },
    [applySession]
  );

  const logout = React.useCallback<AuthContextValue["logout"]>(async () => {
    try {
      await postJson("/api/auth/logout", {}, accessTokenRef.current);
    } catch {
      /* logout is best-effort */
    }
    clearSession();
    router.replace("/login");
  }, [clearSession, router]);

  const value = React.useMemo<AuthContextValue>(
    () => ({ status, user, login, signup, logout, setUser }),
    [status, user, login, signup, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
