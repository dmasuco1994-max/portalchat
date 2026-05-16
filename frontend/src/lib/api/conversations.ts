import { apiFetch } from "./client";
import type { Conversation, Message } from "./types";

export function listConversations(numberId: string) {
  return apiFetch<Conversation[]>(`/numbers/${numberId}/conversations`);
}

export function listMessages(conversationId: string, limit = 100) {
  return apiFetch<Message[]>(
    `/conversations/${conversationId}/messages?limit=${limit}`
  );
}

export interface SendTextInput {
  to: string;
  text: string;
}

export function sendText(numberId: string, input: SendTextInput) {
  return apiFetch<Record<string, unknown>>(
    `/numbers/${numberId}/messages/text`,
    {
      method: "POST",
      body: input,
    }
  );
}
