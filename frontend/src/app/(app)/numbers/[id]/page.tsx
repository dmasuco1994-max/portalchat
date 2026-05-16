"use client";

import * as React from "react";
import Link from "next/link";
import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, MessageSquare, PhoneOff, Trash2, Webhook } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { PageHeader } from "@/components/app/page-header";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { QrDisplay } from "@/components/numbers/qr-display";
import { StatusBadge } from "@/components/numbers/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useDeleteNumber,
  useDisconnectNumber,
  useNumber,
  useNumberQr,
  useNumberStatusPolling,
} from "@/lib/hooks/use-numbers";

export default function NumberDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const canManage = user?.role === "owner" || user?.role === "admin";

  const numberQuery = useNumber(id);
  const statusQuery = useNumberStatusPolling(id, numberQuery.data?.status);
  const qrQuery = useNumberQr(
    id,
    canManage ? numberQuery.data?.status : undefined
  );

  const disconnect = useDisconnectNumber(id);
  const remove = useDeleteNumber(id);

  const [confirmDisconnect, setConfirmDisconnect] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  // Use the polled status when available; otherwise the cached one. This makes
  // the UI react in seconds when the user scans the QR.
  const effectiveStatus = statusQuery.data?.status ?? numberQuery.data?.status;
  const isConnected = effectiveStatus === "connected";
  const isFailed = effectiveStatus === "failed";

  if (numberQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (numberQuery.error || !numberQuery.data) {
    return (
      <div className="space-y-4">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
          ← Back to numbers
        </Link>
        <Card>
          <CardHeader>
            <CardTitle>Number not found</CardTitle>
            <CardDescription>
              {numberQuery.error?.message ?? "It may have been deleted."}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const number = numberQuery.data;

  return (
    <div>
      <Link
        href="/dashboard"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Volver a números
      </Link>

      <PageHeader
        title={number.name}
        description={
          <span className="inline-flex items-center gap-2">
            {effectiveStatus && (
              <StatusBadge status={effectiveStatus} pulse />
            )}
            {number.phone_number ? (
              <span className="font-mono text-sm">+{number.phone_number}</span>
            ) : (
              <span className="text-sm">Sin pairear</span>
            )}
          </span>
        }
        actions={
          <>
            <Button asChild variant="outline">
              <Link href={`/numbers/${id}/conversations`}>
                <MessageSquare className="size-4" />
                Conversaciones
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href={`/numbers/${id}/webhook`}>
                <Webhook className="size-4" />
                Webhook
              </Link>
            </Button>
            {canManage && isConnected && (
              <Button
                variant="outline"
                onClick={() => setConfirmDisconnect(true)}
              >
                <PhoneOff className="size-4" />
                Desconectar
              </Button>
            )}
            {canManage && (
              <Button
                variant="destructive"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 className="size-4" />
                Eliminar
              </Button>
            )}
          </>
        }
      />

      {!isConnected && !isFailed && canManage && (
        <QrDisplay
          qr={qrQuery.data}
          isLoading={qrQuery.isPending}
          error={qrQuery.error}
        />
      )}

      {!isConnected && !isFailed && !canManage && (
        <Card>
          <CardHeader>
            <CardTitle>Esperando a un admin</CardTitle>
            <CardDescription>
              Solo los owners y admins pueden escanear el QR para parear este
              número.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {isConnected && (
        <Card>
          <CardHeader>
            <CardTitle>Conectado</CardTitle>
            <CardDescription>
              Esta línea está activa y recibiendo mensajes.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Teléfono
              </p>
              <p className="mt-0.5 font-mono">+{number.phone_number ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Instancia
              </p>
              <p className="mt-0.5 font-mono">{number.instance_name}</p>
            </div>
            {number.last_connected_at && (
              <div className="sm:col-span-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Última conexión
                </p>
                <p className="mt-0.5">
                  {new Date(number.last_connected_at).toLocaleString()}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {isFailed && (
        <Card>
          <CardHeader>
            <CardTitle>La conexión falló</CardTitle>
            <CardDescription>
              Evolution devolvió un error. Eliminá el número y volvelo a crear
              para empezar de nuevo.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <ConfirmDialog
        open={confirmDisconnect}
        onOpenChange={setConfirmDisconnect}
        title={`¿Desconectar "${number.name}"?`}
        description="La instancia de Evolution sigue corriendo. Podés escanear un nuevo QR para reconectar."
        confirmLabel="Desconectar"
        loading={disconnect.isPending}
        destructive
        onConfirm={async () => {
          try {
            await disconnect.mutateAsync();
            toast.success("Desconectado");
            setConfirmDisconnect(false);
          } catch (e) {
            toast.error(
              e instanceof Error ? e.message : "No pudimos desconectar"
            );
          }
        }}
      />

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={`¿Eliminar "${number.name}"?`}
        description="Eliminamos el número y la instancia de Evolution. Las conversaciones quedan en la base."
        confirmLabel="Eliminar"
        loading={remove.isPending}
        destructive
        onConfirm={async () => {
          try {
            await remove.mutateAsync();
            toast.success("Eliminado");
            setConfirmDelete(false);
            router.push("/dashboard");
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "No pudimos eliminar");
          }
        }}
      />
    </div>
  );
}
