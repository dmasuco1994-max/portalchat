"use client";

import * as React from "react";
import { Copy, Check, KeyRound } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  secret: string | null;
  onDismiss: () => void;
}

export function SecretDisplay({ secret, onDismiss }: Props) {
  const [copied, setCopied] = React.useState(false);

  const onCopy = async () => {
    if (!secret) return;
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Couldn't copy — copy it manually");
    }
  };

  return (
    <Dialog
      open={!!secret}
      onOpenChange={(open) => {
        if (!open) onDismiss();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="size-5" />
            New signing secret
          </DialogTitle>
          <DialogDescription>
            Copy this now — it&apos;s shown <strong>only once</strong>. Use it on
            your CRM to verify the <code>X-WhatsApp-Portal-Signature</code> HMAC
            header on incoming webhooks.
          </DialogDescription>
        </DialogHeader>
        <pre className="overflow-x-auto rounded-md border bg-muted/40 p-3 font-mono text-xs">
          {secret}
        </pre>
        <DialogFooter>
          <Button variant="outline" onClick={onCopy}>
            {copied ? (
              <Check className="size-4" />
            ) : (
              <Copy className="size-4" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button onClick={onDismiss}>I&apos;ve saved it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
