"use client";

import * as React from "react";
import Link from "next/link";
import { use } from "react";
import { ArrowLeft, Phone } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { ContactAvatar } from "@/components/conversations/contact-avatar";
import { MessageBubble } from "@/components/conversations/message-bubble";
import { SendTextForm } from "@/components/conversations/send-text-form";
import { Skeleton } from "@/components/ui/skeleton";
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
    ? "Solo los owners y admins pueden mandar mensajes."
    : numberStatus !== "connected"
      ? "El número no está conectado — pareálo antes de mandar."
      : !conversation
        ? "Cargando conversación…"
        : undefined;

  const headerName = conversation ? headerLabel(conversation) : "Conversación";

  return (
    <div className="-mx-6 -my-8 flex h-[calc(100vh-0px)] flex-col lg:-mx-10">
      <header className="flex items-center gap-4 border-b bg-card px-6 py-4 lg:px-10">
        <Link
          href={`/numbers/${id}/conversations`}
          className="flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Volver"
        >
          <ArrowLeft className="size-4" />
        </Link>
        <ContactAvatar
          name={headerName}
          pictureUrl={conversation?.profile_picture_url}
          size="md"
        />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold leading-tight">
            {headerName}
          </h1>
          {conversation?.remote_phone && (
            <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
              <Phone className="size-3" />
              <span className="font-mono">+{conversation.remote_phone}</span>
            </p>
          )}
        </div>
      </header>

      <div
        ref={scrollerRef}
        className="flex-1 space-y-2 overflow-y-auto bg-muted/30 px-6 py-6 lg:px-10"
      >
        {messagesQuery.isPending && (
          <div className="space-y-3">
            <Skeleton className="ml-auto h-10 w-2/3 rounded-2xl" />
            <Skeleton className="h-10 w-1/2 rounded-2xl" />
            <Skeleton className="ml-auto h-10 w-3/4 rounded-2xl" />
          </div>
        )}
        {messagesQuery.error && (
          <p className="text-center text-sm text-destructive">
            {messagesQuery.error.message}
          </p>
        )}
        {ordered.length === 0 && !messagesQuery.isPending && (
          <p className="text-center text-sm text-muted-foreground">
            Todavía no hay mensajes en esta conversación.
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
