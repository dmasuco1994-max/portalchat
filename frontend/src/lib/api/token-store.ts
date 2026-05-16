// Module-level access-token holder. The token lives ONLY in memory so XSS
// can't lift it from localStorage. The httpOnly refresh cookie set by the
// Next route handlers is what survives page reloads.

type Listener = (token: string | null) => void;

let currentToken: string | null = null;
const listeners = new Set<Listener>();

export function getAccessToken(): string | null {
  return currentToken;
}

export function setAccessToken(token: string | null) {
  currentToken = token;
  for (const l of listeners) l(token);
}

export function subscribeAccessToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
