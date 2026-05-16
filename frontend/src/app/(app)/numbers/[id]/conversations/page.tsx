"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft, MessageCircle } from "lucide-react";

import { EmptyState } from "@/components/app/empty-state";
import { PageHeader } from "@/components/app/page-header";
import { ConversationListItem } from "@/components/conversations/conversation-list-item";
import { Skeleton } from "@/components/ui/skeleton";
import { useNumber } from "@/lib/hooks/use-numbers";
import { useConversations } from "@/lib/hooks/use-conversations";

export default function ConversationsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const numberQuery = useNumber(id);
  const conversationsQuery = useConversations(id);

  return (
    <div>
      <Link
        href={`/numbers/${id}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Volver al número
      </Link>

      <PageHeader
        title={numberQuery.data?.name ?? "Conversaciones"}
        description="Ordenadas por actividad más reciente. Polling cada 5 segundos."
      />

      {conversationsQuery.isPending && (
        <div className="grid gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
          ))}
        </div>
      )}

      {conversationsQuery.error && (
        <p className="text-sm text-destructive">
          {conversationsQuery.error.message}
        </p>
      )}

      {conversationsQuery.data && conversationsQuery.data.length === 0 && (
        <EmptyState
          icon={<MessageCircle className="size-6" />}
          title="Todavía no hay conversaciones"
          description="Cuando un contacto le escriba a este número por WhatsApp, va a aparecer acá automáticamente."
        />
      )}

      {conversationsQuery.data && conversationsQuery.data.length > 0 && (
        <div className="grid gap-2">
          {conversationsQuery.data.map((c) => (
            <ConversationListItem key={c.id} numberId={id} conversation={c} />
          ))}
        </div>
      )}
    </div>
  );
}
