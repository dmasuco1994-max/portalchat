const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000/api/v1";

export interface BackendErrorBody {
  detail?: string | Array<{ msg?: string; loc?: unknown[] }>;
}

export interface BackendResponse<T> {
  ok: boolean;
  status: number;
  data?: T;
  error?: string;
}

function extractError(body: BackendErrorBody | undefined): string {
  if (!body?.detail) return "Request failed";
  if (typeof body.detail === "string") return body.detail;
  return body.detail.map((d) => d.msg ?? "invalid").join("; ");
}

export async function backendFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<BackendResponse<T>> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  const contentType = res.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const body = isJson ? await res.json().catch(() => undefined) : undefined;

  if (!res.ok) {
    return { ok: false, status: res.status, error: extractError(body) };
  }
  return { ok: true, status: res.status, data: body as T };
}

export const backendUrl = BACKEND_URL;
