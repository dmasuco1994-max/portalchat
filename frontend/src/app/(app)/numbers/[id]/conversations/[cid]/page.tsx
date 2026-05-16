"use client";

import * as React from "react";
import Link from "next/link";
import { use } from "react";
import { ArrowLeft } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { MessageBubble } from "@/components/conversations/message-bubble";
import { SendTextForm } from "@/components/conversations/send-text-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Conversation } from "@/lib/api/types";
import { useConversations, useMessages } from "@/lib/hooks/use-conversations";
import { useNumber } from "@/lib/hooks/use-numbers";

function recipientDigits(c: Conversation): string {
  if (c.remote_phone) return c.remote_phone;
  const before = c.remote_jid.split("@")[0];
  return before.replace(/\D/g, "");
}

function headerLabel(c: Conversation): string {
  if (c.remote_name) return c.remote_name;
  if (c.remote_phone) return `+${c.remote_phone}`;
  return c.remote_jid;
}

export default function ConversationViewerPage({
  params,
}: {
  params: Promise<{ id: string; cid: string }>;
}) {
  const { id, cid } = use(params);
  const { user } = useAuth();
  const canSend = user?.role === "owner" || user?.role === "admin";

  const numberQuery = useNumber(id);
  const conversationsQuery = useConversations(id);
  const messagesQuery = useMessages(cid);

  const conversation = conversationsQuery.data?.find((c) => c.id === cid);

  // Backend returns newest first (limit-paginated). Reverse for chat layout
  // (oldest at the top, newest at the bottom).
  const ordered = React.useMemo(() => {
    if (!messagesQuery.data) return [];
    return [...messagesQuery.data].reverse();
  }, [messagesQuery.data]);

  const scrollerRef = React.useRef<HTMLDivElement | null>(null);
  const lastMessageId = ordered.at(-1)?.id ?? null;

  React.useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lastMessageId, cid]);

  const numberStatus = numberQuery.data?.status;
  const sendDisabled = !canSend || numberStatus !== "connected" || !conversation;
  const disabledReason = !canSend
    ? "Only owners and admins can send messages."
    : numberStatus !== "connected"
      ? "This number is not connected — pair it before sending."
      : !conversation
        ? "Conversation not loaded yet."
        : undefined;

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex items-center justify-between gap-4 border-b pb-3">
        <div className="min-w-0">
          <Link
            href={`/numbers/${id}/conversations`}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
          >
            <ArrowLeft className="size-4" />
            Back to conversations
          </Link>
          <h1 className="mt-1 truncate text-xl font-semibold tracking-tight">
            {conversation ? headerLabel(conversation) : "Conversation"}
          </h1>
          {conversation?.remote_phone && (
            <p className="truncate text-sm text-muted-foreground">
              +{conversation.remote_phone}
            </p>
          )}
        </div>
      </div>

      <div
        ref={scrollerRef}
        className="flex-1 space-y-2 overflow-y-auto bg-muted/20 p-4"
      >
        {messagesQuery.isPending && (
          <p className="text-center text-sm text-muted-foreground">
            Loading messages…
          </p>
        )}
        {messagesQuery.error && (
          <Card>
            <CardHeader>
              <CardTitle>Couldn&apos;t load messages</CardTitle>
              <CardDescription>{messagesQuery.error.message}</CardDescription>
            </CardHeader>
            <CardContent />
          </Card>
        )}
        {ordered.length === 0 && !messagesQuery.isPending && (
          <p className="text-center text-sm text-muted-foreground">
            No messages in this conversation yet.
          </p>
        )}
        {ordered.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      <SendTextForm
        numberId={id}
        conversationId={cid}
        recipientDigits={conversation ? recipientDigits(conversation) : ""}
        disabled={sendDisabled}
        disabledReason={disabledReason}
      />
    </div>
  );
}
