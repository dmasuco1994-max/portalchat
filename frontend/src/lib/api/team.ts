import { apiFetch } from "./client";
import type { Role, User } from "./types";

export function listUsers() {
  return apiFetch<User[]>("/users");
}

export interface InviteInput {
  email: string;
  full_name: string;
  role: Role;
  password: string;
}

export function inviteUser(input: InviteInput) {
  return apiFetch<User>("/users/invite", { method: "POST", body: input });
}

export interface UpdateUserInput {
  full_name?: string;
  role?: Role;
  is_active?: boolean;
}

export function updateUser(userId: string, input: UpdateUserInput) {
  return apiFetch<User>(`/users/${userId}`, { method: "PATCH", body: input });
}

export function deleteUser(userId: string) {
  return apiFetch<void>(`/users/${userId}`, { method: "DELETE" });
}
