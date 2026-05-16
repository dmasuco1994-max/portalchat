"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { PageHeader } from "@/components/app/page-header";
import { Skeleton } from "@/components/ui/skeleton";
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
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Volver al número
      </Link>

      <PageHeader
        title="Webhook"
        description={numberQuery.data?.name ?? "Número"}
      />

      {!canManage && (
        <Card>
          <CardHeader>
            <CardTitle>Solo lectura</CardTitle>
            <CardDescription>
              Solo los owners y admins pueden editar la configuración del
              webhook.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {numberQuery.isPending && (
        <Skeleton className="h-[400px] w-full rounded-xl" />
      )}

      {numberQuery.data && canManage && (
        <WebhookForm number={numberQuery.data} />
      )}

      {numberQuery.data && !canManage && numberQuery.data.webhook_url && (
        <Card>
          <CardHeader>
            <CardTitle>Configuración actual</CardTitle>
            <CardDescription>
              <span className="break-all font-mono">{numberQuery.data.webhook_url}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm">
            <p>
              Estado:{" "}
              {numberQuery.data.webhook_active ? "Activo" : "Pausado"}
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
