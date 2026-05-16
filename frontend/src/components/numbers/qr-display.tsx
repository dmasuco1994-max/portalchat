"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { QrCode } from "@/lib/api/types";

function normalizeDataUri(raw: string): string {
  if (raw.startsWith("data:")) return raw;
  return `data:image/png;base64,${raw}`;
}

interface Props {
  qr?: QrCode;
  isLoading: boolean;
  error?: Error | null;
}

export function QrDisplay({ qr, isLoading, error }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scan to pair</CardTitle>
        <CardDescription>
          On WhatsApp: Settings → Linked devices → Link a device. The QR
          refreshes automatically.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        {isLoading && !qr && (
          <div className="flex h-64 w-64 items-center justify-center rounded-md border bg-muted/40">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && !qr && (
          <p className="text-sm text-destructive">{error.message}</p>
        )}

        {qr?.qr_base64 && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={normalizeDataUri(qr.qr_base64)}
            alt="WhatsApp pairing QR"
            className="h-64 w-64 rounded-md border bg-white p-2"
          />
        )}

        {qr?.pairing_code && (
          <div className="text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Or pair with code
            </p>
            <p className="font-mono text-lg tracking-widest">
              {qr.pairing_code}
            </p>
          </div>
        )}

        {qr && !qr.qr_base64 && !qr.pairing_code && (
          <p className="text-sm text-muted-foreground">
            Waiting for Evolution to produce a QR…
          </p>
        )}
      </CardContent>
    </Card>
  );
}
