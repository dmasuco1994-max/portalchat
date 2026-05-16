"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, ImageOff, Loader2 } from "lucide-react";

import { rawFetchMedia } from "@/lib/api/client";
import { cn } from "@/lib/utils";

/** Fetch the bytes of a media message and return an object URL.
 *  Returns null while loading and on error (component decides what to show).
 *  Revokes the URL automatically when the component unmounts or the message
 *  id changes. */
function useMediaBlobUrl(messageId: string) {
  const query = useQuery({
    queryKey: ["media", messageId],
    queryFn: async () => {
      const res = await rawFetchMedia(`/messages/${messageId}/media`);
      const blob = await res.blob();
      return { url: URL.createObjectURL(blob), blob };
    },
    staleTime: Infinity,
    gcTime: 5 * 60 * 1000,
    retry: 1,
  });

  React.useEffect(() => {
    const url = query.data?.url;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [query.data?.url]);

  return query;
}

export function MediaImage({
  messageId,
  alt,
  className,
}: {
  messageId: string;
  alt?: string;
  className?: string;
}) {
  const { data, isPending, error } = useMediaBlobUrl(messageId);
  if (isPending) {
    return (
      <div
        className={cn(
          "flex aspect-square w-56 items-center justify-center rounded-lg bg-muted",
          className
        )}
      >
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div
        className={cn(
          "flex aspect-square w-56 items-center justify-center rounded-lg border bg-muted/40 text-muted-foreground",
          className
        )}
      >
        <ImageOff className="size-6" />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={data.url}
      alt={alt ?? "Imagen"}
      className={cn(
        "max-h-80 max-w-xs rounded-lg object-contain",
        className
      )}
      loading="lazy"
    />
  );
}

export function MediaSticker({
  messageId,
  className,
}: {
  messageId: string;
  className?: string;
}) {
  const { data, isPending, error } = useMediaBlobUrl(messageId);
  if (isPending || error || !data) {
    // Stickers fall back to a compact placeholder when not available.
    return null;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={data.url}
      alt="Sticker"
      className={cn("size-32", className)}
      loading="lazy"
    />
  );
}

export function MediaAudio({ messageId }: { messageId: string }) {
  const { data, isPending, error } = useMediaBlobUrl(messageId);
  if (isPending) {
    return (
      <div className="flex h-10 w-64 items-center gap-2 rounded-full bg-background/40 px-3 text-xs text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Cargando audio…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex h-10 w-64 items-center gap-2 rounded-full bg-background/40 px-3 text-xs text-muted-foreground">
        <ImageOff className="size-4" />
        No pudimos cargar el audio
      </div>
    );
  }
  return (
    // Plain <audio> takes care of seeking + play/pause natively across browsers.
    <audio
      controls
      preload="metadata"
      src={data.url}
      className="h-10 w-64"
    />
  );
}

export function MediaVideo({ messageId }: { messageId: string }) {
  const { data, isPending, error } = useMediaBlobUrl(messageId);
  if (isPending) {
    return (
      <div className="flex aspect-video w-72 items-center justify-center rounded-lg bg-muted">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex aspect-video w-72 items-center justify-center rounded-lg border bg-muted/40 text-muted-foreground">
        <ImageOff className="size-6" />
      </div>
    );
  }
  return (
    <video
      controls
      preload="metadata"
      src={data.url}
      className="max-h-80 max-w-sm rounded-lg"
    />
  );
}

export function MediaDocument({
  messageId,
  fileName,
}: {
  messageId: string;
  fileName?: string | null;
}) {
  const { data, isPending, error } = useMediaBlobUrl(messageId);
  const label = fileName ?? "Documento";
  if (isPending) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        <span>Cargando documento…</span>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm text-muted-foreground">
        <FileText className="size-4" />
        <span>{label}</span>
        <span className="text-xs">(no disponible)</span>
      </div>
    );
  }
  return (
    <a
      href={data.url}
      download={fileName ?? `documento-${messageId}.bin`}
      className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm hover:bg-background/60"
    >
      <FileText className="size-4 shrink-0" />
      <span className="truncate">{label}</span>
      <Download className="size-3.5 shrink-0 opacity-60" />
    </a>
  );
}
