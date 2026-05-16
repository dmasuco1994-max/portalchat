"use client";

import * as React from "react";
import Link from "next/link";
import { use } from "react";
import { ArrowLeft, MessageCircle, Search, X } from "lucide-react";

import { EmptyState } from "@/components/app/empty-state";
import { PageHeader } from "@/components/app/page-header";
import { ConversationListItem } from "@/components/conversations/conversation-list-item";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Conversation } from "@/lib/api/types";
import { useNumber } from "@/lib/hooks/use-numbers";
import { useConversations } from "@/lib/hooks/use-conversations";

function normalize(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function matches(c: Conversation, query: string): boolean {
  if (!query) return true;
  const haystack = normalize(
    [c.remote_name, c.remote_phone, c.remote_jid].filter(Boolean).join(" ")
  );
  // Tokenize query so "juan 1234" matches "Juan Pérez +5491134567890"
  return normalize(query)
    .split(/\s+/)
    .filter(Boolean)
    .every((token) => haystack.includes(token));
}

export default function ConversationsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const numberQuery = useNumber(id);
  const conversationsQuery = useConversations(id);

  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    if (!conversationsQuery.data) return [];
    return conversationsQuery.data.filter((c) => matches(c, query));
  }, [conversationsQuery.data, query]);

  const total = conversationsQuery.data?.length ?? 0;
  const hasSearch = query.trim().length > 0;

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
        accentClass="accent-conversations"
      />

      <div className="mb-4 relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nombre, teléfono…"
          className="pl-9 pr-10"
          aria-label="Buscar conversaciones"
        />
        {hasSearch && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Limpiar búsqueda"
          >
            <X className="size-4" />
          </button>
        )}
        {hasSearch && total > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            {filtered.length} de {total} conversaciones
          </p>
        )}
      </div>

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

      {conversationsQuery.data && total === 0 && (
        <EmptyState
          icon={<MessageCircle className="size-6" />}
          title="Todavía no hay conversaciones"
          description="Cuando un contacto le escriba a este número por WhatsApp, va a aparecer acá automáticamente."
        />
      )}

      {conversationsQuery.data && total > 0 && filtered.length === 0 && (
        <EmptyState
          icon={<Search className="size-6" />}
          title="Sin coincidencias"
          description={`Ninguna conversación matchea "${query}". Probá con menos palabras o limpiá el filtro.`}
        />
      )}

      {filtered.length > 0 && (
        <div className="grid gap-2">
          {filtered.map((c) => (
            <ConversationListItem key={c.id} numberId={id} conversation={c} />
          ))}
        </div>
      )}
    </div>
  );
}
