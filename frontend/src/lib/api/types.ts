export type Role = "owner" | "admin" | "member";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type NumberStatus =
  | "created"
  | "connecting"
  | "connected"
  | "disconnected"
  | "failed";

export interface WhatsAppNumber {
  id: string;
  organization_id: string;
  name: string;
  instance_name: string;
  phone_number: string | null;
  status: NumberStatus;
  last_connected_at: string | null;
  webhook_url: string | null;
  webhook_active: boolean;
  webhook_events: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface QrCode {
  instance_name: string;
  status: NumberStatus;
  qr_base64: string | null;
  pairing_code: string | null;
}

export interface ConnectionStatus {
  instance_name: string;
  status: NumberStatus;
  raw_state: string | null;
}

export interface Conversation {
  id: string;
  whatsapp_number_id: string;
  remote_jid: string;
  remote_phone: string | null;
  remote_name: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export type MessageDirection = "inbound" | "outbound";
export type MessageContentType =
  | "text"
  | "image"
  | "audio"
  | "video"
  | "document"
  | "sticker"
  | "location"
  | "contact"
  | "reaction"
  | "unknown";
export type MessageDeliveryStatus =
  | "pending"
  | "sent"
  | "delivered"
  | "read"
  | "failed";

export interface Message {
  id: string;
  conversation_id: string;
  whatsapp_number_id: string;
  direction: MessageDirection;
  evolution_message_id: string;
  from_jid: string;
  to_jid: string;
  content_type: MessageContentType;
  content_text: string | null;
  media_url: string | null;
  status: MessageDeliveryStatus;
  sent_at: string;
  created_at: string;
}

export interface WebhookConfigResponse {
  url: string | null;
  events: string[] | null;
  active: boolean;
  /** Only present on the response that creates or rotates the secret. */
  secret: string | null;
}

export interface WebhookConfigUpdate {
  /** Pass null to clear the URL. Omit to keep current. */
  url?: string | null;
  events?: string[] | null;
  active?: boolean;
  rotate_secret?: boolean;
}

export type WebhookDeliveryStatus =
  | "pending"
  | "in_progress"
  | "success"
  | "failed"
  | "abandoned";

export interface WebhookDelivery {
  id: string;
  whatsapp_number_id: string;
  target_url: string;
  event_type: string;
  attempts: number;
  max_attempts: number;
  status: WebhookDeliveryStatus;
  last_attempt_at: string | null;
  next_retry_at: string | null;
  completed_at: string | null;
  response_status: number | null;
  response_body_excerpt: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
