import Link from "next/link";
import { ChevronRight, MessageCircle } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
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
  return (
    <Link
      href={`/numbers/${numberId}/conversations/${conversation.id}`}
      className="block"
    >
      <Card className="transition-colors hover:bg-muted/40">
        <CardContent className="flex items-center gap-3 p-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <MessageCircle className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate font-medium">{displayLabel(conversation)}</p>
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
          <ChevronRight className="size-4 text-muted-foreground" />
        </CardContent>
      </Card>
    </Link>
  );
}
