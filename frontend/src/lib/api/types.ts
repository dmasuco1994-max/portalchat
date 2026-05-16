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
