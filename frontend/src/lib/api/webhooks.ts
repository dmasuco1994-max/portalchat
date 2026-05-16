import { apiFetch } from "./client";
import type {
  WebhookConfigResponse,
  WebhookConfigUpdate,
  WebhookDelivery,
} from "./types";

/** Events the backend forwards. Source of truth: services.evolution + webhook_inbound. */
export const SUPPORTED_EVENTS = [
  "MESSAGES_UPSERT",
  "MESSAGES_UPDATE",
  "CONNECTION_UPDATE",
  "QRCODE_UPDATED",
  "SEND_MESSAGE",
] as const;

export type SupportedEvent = (typeof SUPPORTED_EVENTS)[number];

export function updateWebhookConfig(
  numberId: string,
  payload: WebhookConfigUpdate
) {
  return apiFetch<WebhookConfigResponse>(`/numbers/${numberId}/webhook`, {
    method: "PATCH",
    body: payload,
  });
}

export function listWebhookDeliveries(numberId: string, limit = 50) {
  return apiFetch<WebhookDelivery[]>(
    `/numbers/${numberId}/webhook-deliveries?limit=${limit}`
  );
}
