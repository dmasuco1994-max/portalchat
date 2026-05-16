"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft } from "lucide-react";

import { ConversationListItem } from "@/components/conversations/conversation-list-item";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
    <div className="space-y-6">
      <Link
        href={`/numbers/${id}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
      >
        <ArrowLeft className="size-4" />
        Back to number
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {numberQuery.data?.name ?? "Conversations"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Most recently active first.
        </p>
      </div>

      {conversationsQuery.isPending && (
        <p className="text-sm text-muted-foreground">Loading conversations…</p>
      )}

      {conversationsQuery.error && (
        <Card>
          <CardHeader>
            <CardTitle>Couldn&apos;t load conversations</CardTitle>
            <CardDescription>
              {conversationsQuery.error.message}
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {conversationsQuery.data && conversationsQuery.data.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>No conversations yet</CardTitle>
            <CardDescription>
              Once a contact sends a message to this number, it&apos;ll show up
              here.
            </CardDescription>
          </CardHeader>
          <CardContent />
        </Card>
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
