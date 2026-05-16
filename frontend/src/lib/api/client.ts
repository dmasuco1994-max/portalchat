import { API_BASE } from "./config";
import { getAccessToken, setAccessToken } from "./token-store";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

type FetchInput = string;

interface ApiFetchInit extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip the silent-refresh retry on 401 (used by auth endpoints themselves). */
  skipRefresh?: boolean;
}

let onAuthFailHandler: (() => void) | null = null;

export function setOnAuthFail(handler: (() => void) | null) {
  onAuthFailHandler = handler;
}

let inflightRefresh: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (inflightRefresh) return inflightRefresh;
  inflightRefresh = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "same-origin",
      });
      if (!res.ok) return null;
      const data = (await res.json()) as { access_token?: string };
      const token = data.access_token ?? null;
      setAccessToken(token);
      return token;
    } catch {
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();
  return inflightRefresh;
}

async function rawFetch(path: FetchInput, init: ApiFetchInit, token: string | null) {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
}

export async function apiFetch<T = unknown>(
  path: FetchInput,
  init: ApiFetchInit = {}
): Promise<T> {
  let token = getAccessToken();
  let res = await rawFetch(path, init, token);

  if (res.status === 401 && !init.skipRefresh) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      onAuthFailHandler?.();
      throw new ApiError(401, "Unauthenticated");
    }
    token = newToken;
    res = await rawFetch(path, init, token);
  }

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      detail = await res.json();
    } catch {
      /* non-json body */
    }
    const message =
      (detail as { detail?: string } | undefined)?.detail ?? `HTTP ${res.status}`;
    throw new ApiError(res.status, String(message), detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Fetch binary media (or any non-JSON body) and return the raw Response.
 *  Auth header is injected and 401 triggers silent-refresh + retry just like
 *  the JSON path. The caller is responsible for reading the body (blob,
 *  arrayBuffer, etc.) and calling URL.revokeObjectURL when done. */
export async function rawFetchMedia(path: FetchInput): Promise<Response> {
  let token = getAccessToken();
  let res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      onAuthFailHandler?.();
      throw new ApiError(401, "Unauthenticated");
    }
    token = newToken;
    res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  if (!res.ok) {
    throw new ApiError(res.status, `HTTP ${res.status}`);
  }
  return res;
}

/** Upload a file via multipart/form-data. Returns the parsed JSON response.
 *  Used for the outbound media endpoint. */
export async function apiUploadFile<T = unknown>(
  path: FetchInput,
  formData: FormData
): Promise<T> {
  let token = getAccessToken();
  const doFetch = (auth: string | null) =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: formData,
      headers: auth ? { Authorization: `Bearer ${auth}` } : {},
    });

  let res = await doFetch(token);
  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      onAuthFailHandler?.();
      throw new ApiError(401, "Unauthenticated");
    }
    token = newToken;
    res = await doFetch(token);
  }

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      detail = await res.json();
    } catch {
      /* non-json body */
    }
    const message =
      (detail as { detail?: string } | undefined)?.detail ??
      `HTTP ${res.status}`;
    throw new ApiError(res.status, String(message), detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
