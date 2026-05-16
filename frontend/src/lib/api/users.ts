import { apiFetch } from "./client";
import type { User } from "./types";

export function getMe() {
  return apiFetch<User>("/users/me");
}
