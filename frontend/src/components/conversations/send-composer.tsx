"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Mic, Paperclip, Send, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { sendMedia } from "@/lib/api/media";
import { useSendText } from "@/lib/hooks/use-conversations";
import { cn } from "@/lib/utils";

interface Props {
  numberId: string;
  conversationId: string;
  recipientDigits: string;
  disabled?: boolean;
  disabledReason?: string;
}

const ACCEPT =
  "image/jpeg,image/png,image/webp,image/gif,video/mp4,audio/*,application/pdf";

function isImageFile(f: File) {
  return f.type.startsWith("image/");
}
function isVideoFile(f: File) {
  return f.type.startsWith("video/");
}
function isAudioFile(f: File) {
  return f.type.startsWith("audio/");
}

function FilePreview({
  file,
  onRemove,
}: {
  file: File;
  onRemove: () => void;
}) {
  const previewUrl = React.useMemo(() => {
    if (isImageFile(file) || isVideoFile(file)) {
      return URL.createObjectURL(file);
    }
    return null;
  }, [file]);
  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return (
    <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-2">
      <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-md bg-background">
        {isImageFile(file) && previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="preview"
            className="size-full object-cover"
          />
        ) : isVideoFile(file) && previewUrl ? (
          <video src={previewUrl} className="size-full object-cover" muted />
        ) : isAudioFile(file) ? (
          <Mic className="size-6 text-muted-foreground" />
        ) : (
          <Paperclip className="size-6 text-muted-foreground" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{file.name}</p>
        <p className="text-xs text-muted-foreground">
          {(file.size / 1024).toFixed(1)} KB · {file.type || "binario"}
        </p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onRemove}
        aria-label="Quitar adjunto"
      >
        <X className="size-4" />
      </Button>
    </div>
  );
}

export function SendComposer({
  numberId,
  conversationId,
  recipientDigits,
  disabled = false,
  disabledReason,
}: Props) {
  const [text, setText] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [sending, setSending] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const send = useSendText(numberId, conversationId);
  const qc = useQueryClient();

  const reset = () => {
    setText("");
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const onSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (disabled || sending) return;

    const trimmed = text.trim();

    if (file) {
      setSending(true);
      try {
        await sendMedia(numberId, recipientDigits, file, trimmed || undefined);
        reset();
        // Force the messages query to refresh quickly — Evolution will fire a
        // SEND_MESSAGE webhook that persists the message, and the 3s poll will
        // pick it up. We invalidate eagerly so the UI updates sooner.
        qc.invalidateQueries({
          queryKey: ["conversations", conversationId, "messages"],
        });
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "No pudimos enviar");
      } finally {
        setSending(false);
      }
      return;
    }

    if (!trimmed) return;
    try {
      await send.mutateAsync({ to: recipientDigits, text: trimmed });
      setText("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "No pudimos enviar");
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSubmit();
    }
  };

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const placeholder = disabled
    ? "Envío deshabilitado"
    : file
      ? isImageFile(file) || isVideoFile(file)
        ? "Agregá un caption (opcional)…"
        : "Adjunto listo — Enter para enviar"
      : "Escribí un mensaje…";

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-2 border-t bg-card p-3 lg:px-10"
    >
      {disabled && disabledReason && (
        <p className="text-xs text-muted-foreground">{disabledReason}</p>
      )}
      {file && <FilePreview file={file} onRemove={() => setFile(null)} />}
      <div className="flex items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          onChange={onPickFile}
          className="hidden"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Adjuntar archivo"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || sending}
          className="shrink-0"
        >
          <Paperclip className={cn("size-4", file && "text-primary")} />
        </Button>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled || sending || send.isPending}
          className="max-h-40 min-h-[44px] resize-none"
        />
        <Button
          type="submit"
          size="icon"
          disabled={
            disabled ||
            sending ||
            send.isPending ||
            (!file && !text.trim())
          }
          aria-label="Enviar"
          className="shrink-0"
        >
          <Send className="size-4" />
        </Button>
      </div>
    </form>
  );
}
