import { apiFetch } from "./client";
import type { ConnectionStatus, QrCode, WhatsAppNumber } from "./types";

export function listNumbers() {
  return apiFetch<WhatsAppNumber[]>("/numbers");
}

export function getNumber(id: string) {
  return apiFetch<WhatsAppNumber>(`/numbers/${id}`);
}

export function createNumber(input: { name: string }) {
  return apiFetch<WhatsAppNumber>("/numbers", {
    method: "POST",
    body: input,
  });
}

export function getNumberQr(id: string) {
  return apiFetch<QrCode>(`/numbers/${id}/qr`);
}

export function getNumberStatus(id: string) {
  return apiFetch<ConnectionStatus>(`/numbers/${id}/status`);
}

export function disconnectNumber(id: string) {
  return apiFetch<WhatsAppNumber>(`/numbers/${id}/disconnect`, {
    method: "POST",
  });
}

export function deleteNumber(id: string) {
  return apiFetch<void>(`/numbers/${id}`, { method: "DELETE" });
}
