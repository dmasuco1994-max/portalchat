import { apiFetch } from "./client";

export interface NotificationSettings {
  telegram_chat_id: string | null;
  notify_on_number_disconnected: boolean;
  notify_on_webhook_abandoned: boolean;
  has_telegram_bot_token: boolean;
  telegram_bot_token_hint: string | null;
}

export interface NotificationSettingsUpdate {
  telegram_bot_token: string | null;
  telegram_chat_id: string | null;
  notify_on_number_disconnected: boolean;
  notify_on_webhook_abandoned: boolean;
}

export interface TelegramTestResult {
  success: boolean;
  detail: string | null;
}

export function getNotifications() {
  return apiFetch<NotificationSettings>("/settings/notifications");
}

export function updateNotifications(input: NotificationSettingsUpdate) {
  return apiFetch<NotificationSettings>("/settings/notifications", {
    method: "PATCH",
    body: input,
  });
}

export function testNotifications() {
  return apiFetch<TelegramTestResult>("/settings/notifications/test", {
    method: "POST",
  });
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
}

export function getWorkspace() {
  return apiFetch<Workspace>("/settings/workspace");
}

export function updateWorkspace(name: string) {
  return apiFetch<Workspace>("/settings/workspace", {
    method: "PATCH",
    body: { name },
  });
}
