import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { ContactAvatar } from "@/components/conversations/contact-avatar";
import { Card } from "@/components/ui/card";
import type { Conversation } from "@/lib/api/types";

function displayLabel(c: Conversation): string {
  if (c.remote_name) return c.remote_name;
  if (c.remote_phone) return `+${c.remote_phone}`;
  return c.remote_jid;
}

function timeLabel(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  return sameDay
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString();
}

interface Props {
  numberId: string;
  conversation: Conversation;
}

export function ConversationListItem({ numberId, conversation }: Props) {
  const name = displayLabel(conversation);
  return (
    <Link
      href={`/numbers/${numberId}/conversations/${conversation.id}`}
      className="block"
    >
      <Card className="group flex items-center gap-3 p-3 transition-all hover:border-primary/40 hover:shadow-sm">
        <ContactAvatar
          name={name}
          pictureUrl={conversation.profile_picture_url}
          size="md"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-medium">{name}</p>
            <span className="shrink-0 text-xs text-muted-foreground">
              {timeLabel(conversation.last_message_at)}
            </span>
          </div>
          <p className="truncate text-sm text-muted-foreground">
            {conversation.remote_phone
              ? `+${conversation.remote_phone}`
              : conversation.remote_jid}
          </p>
        </div>
        <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
      </Card>
    </Link>
  );
}
