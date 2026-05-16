"use client";

import * as React from "react";
import { Check, Copy, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
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

/** WhatsApp pair-by-code is always 8 characters (usually rendered as
 *  `XXXX-YYYY` on the phone). Anything longer than this is almost certainly
 *  Evolution leaking the raw QR payload into the `code` field — we hide it
 *  rather than render a wall of garbage. */
function tidyPairingCode(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim().toUpperCase();
  if (trimmed.length === 0 || trimmed.length > 16) return null;
  // Format 8 alphanumeric chars as XXXX-YYYY for readability if not already
  // formatted.
  if (/^[A-Z0-9]{8}$/.test(trimmed)) {
    return `${trimmed.slice(0, 4)}-${trimmed.slice(4)}`;
  }
  return trimmed;
}

interface Props {
  qr?: QrCode;
  isLoading: boolean;
  error?: Error | null;
}

export function QrDisplay({ qr, isLoading, error }: Props) {
  const pairingCode = tidyPairingCode(qr?.pairing_code);
  const [copied, setCopied] = React.useState(false);

  const onCopy = async () => {
    if (!pairingCode) return;
    try {
      await navigator.clipboard.writeText(pairingCode.replace(/-/g, ""));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      toast.success("Código copiado");
    } catch {
      toast.error("No pudimos copiar — copialo manual");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Escaneá para parear</CardTitle>
        <CardDescription>
          En WhatsApp: Ajustes → Dispositivos vinculados → Vincular un
          dispositivo. El QR se renueva solo.
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
            alt="QR de pareo de WhatsApp"
            className="h-64 w-64 rounded-md border bg-white p-2"
          />
        )}

        {pairingCode && (
          <div className="flex w-full max-w-xs flex-col items-center gap-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              O pareá con código
            </p>
            <div className="flex w-full items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2">
              <code className="flex-1 select-all text-center font-mono text-lg tracking-widest">
                {pairingCode}
              </code>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onCopy}
                aria-label="Copiar código"
                className="shrink-0"
              >
                {copied ? (
                  <Check className="size-4" />
                ) : (
                  <Copy className="size-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              En WhatsApp: Vincular un dispositivo → Vincular con número de
              teléfono.
            </p>
          </div>
        )}

        {qr && !qr.qr_base64 && !pairingCode && (
          <p className="text-sm text-muted-foreground">
            Esperando a que Evolution genere el QR…
          </p>
        )}
      </CardContent>
    </Card>
  );
}
