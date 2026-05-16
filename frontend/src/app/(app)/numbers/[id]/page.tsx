"use client";

import * as React from "react";
import Link from "next/link";
import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, PhoneOff, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
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
    <div className="space-y-6">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
      >
        <ArrowLeft className="size-4" />
        Back to numbers
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{number.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            {effectiveStatus && <StatusBadge status={effectiveStatus} />}
            {number.phone_number && (
              <span className="text-sm text-muted-foreground">
                +{number.phone_number}
              </span>
            )}
          </div>
        </div>
        {canManage && (
          <div className="flex items-center gap-2">
            {isConnected && (
              <Button
                variant="outline"
                onClick={() => setConfirmDisconnect(true)}
              >
                <PhoneOff className="size-4" />
                Disconnect
              </Button>
            )}
            <Button
              variant="destructive"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="size-4" />
              Delete
            </Button>
          </div>
        )}
      </div>

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
            <CardTitle>Waiting for an admin</CardTitle>
            <CardDescription>
              Only owners and admins can scan the QR to pair this number.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {isConnected && (
        <Card>
          <CardHeader>
            <CardTitle>Paired</CardTitle>
            <CardDescription>
              This line is live and receiving messages.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              <span className="text-muted-foreground">Phone:</span>{" "}
              <span className="font-mono">+{number.phone_number ?? "—"}</span>
            </p>
            <p>
              <span className="text-muted-foreground">Instance:</span>{" "}
              <span className="font-mono">{number.instance_name}</span>
            </p>
            {number.last_connected_at && (
              <p>
                <span className="text-muted-foreground">Last connected:</span>{" "}
                {new Date(number.last_connected_at).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {isFailed && (
        <Card>
          <CardHeader>
            <CardTitle>Connection failed</CardTitle>
            <CardDescription>
              Evolution returned an error. Delete and recreate the number to
              start over.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <ConfirmDialog
        open={confirmDisconnect}
        onOpenChange={setConfirmDisconnect}
        title={`Disconnect "${number.name}"?`}
        description="The Evolution instance keeps running. You can scan a new QR to reconnect."
        confirmLabel="Disconnect"
        loading={disconnect.isPending}
        destructive
        onConfirm={async () => {
          try {
            await disconnect.mutateAsync();
            toast.success("Disconnected");
            setConfirmDisconnect(false);
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Could not disconnect");
          }
        }}
      />

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={`Delete "${number.name}"?`}
        description="This removes the WhatsApp number and its Evolution instance. Conversations stay in the database."
        confirmLabel="Delete"
        loading={remove.isPending}
        destructive
        onConfirm={async () => {
          try {
            await remove.mutateAsync();
            toast.success("Deleted");
            setConfirmDelete(false);
            router.push("/dashboard");
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Could not delete");
          }
        }}
      />
    </div>
  );
}
