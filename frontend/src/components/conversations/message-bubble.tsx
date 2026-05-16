import * as React from "react";
import {
  AlertCircle,
  Check,
  CheckCheck,
  Clock,
  MapPin,
  UserSquare,
} from "lucide-react";

import {
  MediaAudio,
  MediaDocument,
  MediaImage,
  MediaSticker,
  MediaVideo,
} from "@/components/conversations/media-blob";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/api/types";

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusIcon({ status }: { status: Message["status"] }) {
  switch (status) {
    case "pending":
      return <Clock className="size-3 opacity-70" />;
    case "sent":
      return <Check className="size-3 opacity-70" />;
    case "delivered":
      return <CheckCheck className="size-3 opacity-70" />;
    case "read":
      return <CheckCheck className="size-3 text-sky-300" />;
    case "failed":
      return <AlertCircle className="size-3 text-red-300" />;
  }
}

const EMOJI_ONLY_REGEX =
  /^(?:\s|\p{Extended_Pictographic}|\p{Emoji_Component}|️|‍)+$/u;

function isEmojiOnly(text: string | null | undefined): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (!EMOJI_ONLY_REGEX.test(trimmed)) return false;
  const segmenter =
    typeof Intl !== "undefined" && "Segmenter" in Intl
      ? new Intl.Segmenter(undefined, { granularity: "grapheme" })
      : null;
  const count = segmenter
    ? Array.from(segmenter.segment(trimmed)).length
    : trimmed.length;
  return count <= 3;
}

function MediaBody({ message }: { message: Message }) {
  switch (message.content_type) {
    case "image":
      return <MediaImage messageId={message.id} alt={message.content_text ?? "Imagen"} />;
    case "sticker":
      return <MediaSticker messageId={message.id} />;
    case "video":
      return <MediaVideo messageId={message.id} />;
    case "audio":
      return <MediaAudio messageId={message.id} />;
    case "document":
      return (
        <MediaDocument
          messageId={message.id}
          fileName={message.content_text}
        />
      );
    case "location":
      return (
        <div className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm">
          <MapPin className="size-4" />
          <span>Ubicación</span>
        </div>
      );
    case "contact":
      return (
        <div className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm">
          <UserSquare className="size-4" />
          <span>Contacto compartido</span>
        </div>
      );
    default:
      return (
        <p className="italic text-sm opacity-70">[mensaje no soportado]</p>
      );
  }
}

export function MessageBubble({ message }: { message: Message }) {
  const isOutbound = message.direction === "outbound";
  const isReaction = message.content_type === "reaction";

  if (isReaction && message.content_text) {
    return (
      <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
        <div className="rounded-full bg-muted px-2 py-0.5 text-base">
          {message.content_text}
        </div>
      </div>
    );
  }

  const isText = message.content_type === "text";
  const jumbo = isText && isEmojiOnly(message.content_text);

  // Sticker / image / video without caption → render the media bare with the
  // timestamp underneath, no bubble background.
  const isBareMedia =
    (message.content_type === "sticker" ||
      message.content_type === "image" ||
      message.content_type === "video") &&
    !message.content_text;

  if (isBareMedia) {
    return (
      <div
        className={cn(
          "flex flex-col gap-1",
          isOutbound ? "items-end" : "items-start"
        )}
      >
        <MediaBody message={message} />
        <div className="flex items-center gap-1 px-1 text-[10px] text-muted-foreground">
          <span>{timeLabel(message.sent_at)}</span>
          {isOutbound && <StatusIcon status={message.status} />}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] shadow-sm",
          jumbo
            ? "px-1 py-1"
            : "rounded-2xl px-3 py-2 text-sm",
          !jumbo &&
            (isOutbound
              ? "rounded-br-sm bg-primary text-primary-foreground"
              : "rounded-bl-sm bg-card text-card-foreground")
        )}
      >
        {isText ? (
          jumbo ? (
            <p className="text-5xl leading-none">{message.content_text}</p>
          ) : (
            <p className="whitespace-pre-wrap break-words">
              {message.content_text}
            </p>
          )
        ) : (
          <div className="space-y-2">
            <MediaBody message={message} />
            {message.content_text &&
              (message.content_type === "image" ||
                message.content_type === "video") && (
                <p className="whitespace-pre-wrap break-words text-sm">
                  {message.content_text}
                </p>
              )}
          </div>
        )}
        {!jumbo && (
          <div
            className={cn(
              "mt-1 flex items-center justify-end gap-1 text-[10px]",
              isOutbound
                ? "text-primary-foreground/80"
                : "text-muted-foreground"
            )}
          >
            <span>{timeLabel(message.sent_at)}</span>
            {isOutbound && <StatusIcon status={message.status} />}
          </div>
        )}
      </div>
    </div>
  );
}
