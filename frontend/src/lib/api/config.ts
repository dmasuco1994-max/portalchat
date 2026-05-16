// Public-facing backend URL the browser uses directly. CORS for this origin
// is configured on the backend (settings.cors_origins). Server-side code
// inside route handlers uses BACKEND_INTERNAL_URL instead.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
