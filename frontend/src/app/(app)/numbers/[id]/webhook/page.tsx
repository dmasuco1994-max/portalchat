"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { DeliveriesTable } from "@/components/webhook/deliveries-table";
import { WebhookForm } from "@/components/webhook/webhook-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useNumber } from "@/lib/hooks/use-numbers";
import { useWebhookDeliveries } from "@/lib/hooks/use-webhook";

export default function WebhookPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useAuth();
  const canManage = user?.role === "owner" || user?.role === "admin";

  const numberQuery = useNumber(id);
  const deliveriesQuery = useWebhookDeliveries(id);

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
        <h1 className="text-2xl font-semibold tracking-tight">Webhook</h1>
        <p className="text-sm text-muted-foreground">
          {numberQuery.data?.name ?? "Number"}
        </p>
      </div>

      {!canManage && (
        <Card>
          <CardHeader>
            <CardTitle>Read-only</CardTitle>
            <CardDescription>
              Only owners and admins can edit the webhook configuration.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {numberQuery.isPending && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}

      {numberQuery.data && canManage && (
        <WebhookForm number={numberQuery.data} />
      )}

      {numberQuery.data && !canManage && numberQuery.data.webhook_url && (
        <Card>
          <CardHeader>
            <CardTitle>Current configuration</CardTitle>
            <CardDescription>
              <span className="break-all font-mono">{numberQuery.data.webhook_url}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm">
            <p>
              Status:{" "}
              {numberQuery.data.webhook_active ? "Active" : "Paused"}
            </p>
            <p className="text-muted-foreground">
              Events:{" "}
              {numberQuery.data.webhook_events?.join(", ") ?? "All supported"}
            </p>
          </CardContent>
        </Card>
      )}

      {deliveriesQuery.isPending && (
        <p className="text-sm text-muted-foreground">Loading deliveries…</p>
      )}
      {deliveriesQuery.error && (
        <Card>
          <CardHeader>
            <CardTitle>Couldn&apos;t load deliveries</CardTitle>
            <CardDescription>{deliveriesQuery.error.message}</CardDescription>
          </CardHeader>
        </Card>
      )}
      {deliveriesQuery.data && (
        <DeliveriesTable deliveries={deliveriesQuery.data} />
      )}
    </div>
  );
}
