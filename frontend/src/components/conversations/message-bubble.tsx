import * as React from "react";
import {
  AlertCircle,
  Check,
  CheckCheck,
  Clock,
  FileText,
  ImageIcon,
  MapPin,
  Mic,
  Sticker,
  UserSquare,
  Video,
} from "lucide-react";

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

// Matches strings made entirely of emoji + whitespace. Used to "jumbo-ize"
// 1-3 emoji messages (WhatsApp does the same).
const EMOJI_ONLY_REGEX =
  /^(?:\s|\p{Extended_Pictographic}|\p{Emoji_Component}|️|‍)+$/u;

function isEmojiOnly(text: string | null | undefined): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (!EMOJI_ONLY_REGEX.test(trimmed)) return false;
  // Count grapheme clusters to cap "jumbo" at ~3 emojis.
  const segmenter =
    typeof Intl !== "undefined" && "Segmenter" in Intl
      ? new Intl.Segmenter(undefined, { granularity: "grapheme" })
      : null;
  const count = segmenter
    ? Array.from(segmenter.segment(trimmed)).length
    : trimmed.length;
  return count <= 3;
}

const TYPE_LABEL_AND_ICON: Record<
  Message["content_type"],
  { label: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  text: { label: "Texto", Icon: () => null },
  image: { label: "Imagen", Icon: ImageIcon },
  video: { label: "Video", Icon: Video },
  audio: { label: "Audio", Icon: Mic },
  document: { label: "Documento", Icon: FileText },
  sticker: { label: "Sticker", Icon: Sticker },
  location: { label: "Ubicación", Icon: MapPin },
  contact: { label: "Contacto", Icon: UserSquare },
  reaction: { label: "Reacción", Icon: () => null },
  unknown: { label: "Mensaje", Icon: () => null },
};

function MediaPlaceholder({ message }: { message: Message }) {
  const { label, Icon } = TYPE_LABEL_AND_ICON[message.content_type];
  return (
    <div className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-2 text-sm">
      <Icon className="size-4 shrink-0" />
      <div className="min-w-0">
        <p className="font-medium">{label}</p>
        {message.content_text && (
          <p className="truncate text-xs opacity-80">{message.content_text}</p>
        )}
        {!message.content_text && message.content_type === "audio" && (
          <p className="text-xs opacity-70">Nota de voz</p>
        )}
      </div>
    </div>
  );
}

export function MessageBubble({ message }: { message: Message }) {
  const isOutbound = message.direction === "outbound";
  const isReaction = message.content_type === "reaction";

  // Reactions render as a tiny floating chip, not a full bubble.
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
          <>
            <MediaPlaceholder message={message} />
            {message.content_text &&
              message.content_type !== "image" &&
              message.content_type !== "video" && (
                <p className="mt-1 whitespace-pre-wrap break-words">
                  {message.content_text}
                </p>
              )}
          </>
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
