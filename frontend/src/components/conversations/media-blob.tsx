"use client";

import * as React from "react";
import {
  useQuery,
  useQueryClient,
  type QueryCacheNotifyEvent,
} from "@tanstack/react-query";
import { Download, FileText, ImageOff, Loader2 } from "lucide-react";

import { rawFetchMedia } from "@/lib/api/client";
import { cn } from "@/lib/utils";

/** Fetch the bytes of a media message and return a stable object URL.
 *
 *  Lifecycle: we DON'T revoke the URL when a component unmounts. The same
 *  cached entry can have many subscribers (the conversation re-renders on
 *  every 3s poll and components remount in React strict mode). Revoking on
 *  unmount turned the first photo into the only photo — the cached `url`
 *  string survived but pointed to bytes the browser had already freed.
 *
 *  Instead we subscribe to TanStack Query's cache events at module level
 *  and revoke when the entry is actually removed from cache (gcTime expiry
 *  or explicit invalidate). This is the lifecycle that matches the URL's
 *  ownership: the cache owns the bytes, so the cache decides when to free
 *  them. */
const _revokedListenerInstalled = { current: false };

function installRevokeListenerOnce(
  client: ReturnType<typeof useQueryClient>
): void {
  if (_revokedListenerInstalled.current) return;
  _revokedListenerInstalled.current = true;
  client.getQueryCache().subscribe((event: QueryCacheNotifyEvent) => {
    if (event.type === "removed") {
      const key = event.query.queryKey;
      if (Array.isArray(key) && key[0] === "media") {
        const data = event.query.state.data as
          | { url?: string }
          | undefined;
        if (data?.url) URL.revokeObjectURL(data.url);
      }
    }
  });
}

function useMediaBlobUrl(messageId: string) {
  const client = useQueryClient();
  React.useEffect(() => {
    installRevokeListenerOnce(client);
  }, [client]);

  return useQuery({
    queryKey: ["media", messageId],
    queryFn: async () => {
      const res = await rawFetchMedia(`/messages/${messageId}/media`);
      const blob = await res.blob();
      return { url: URL.createObjectURL(blob), blob };
    },
    staleTime: Infinity,
    // Hang onto the bytes longer than the default — re-fetching costs an
    // Evolution round-trip + decryption.
    gcTime: 30 * 60 * 1000,
    retry: 1,
  });
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
