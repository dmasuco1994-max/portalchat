import * as React from "react";
import { AlertCircle, Check, CheckCheck, Clock } from "lucide-react";

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

export function MessageBubble({ message }: { message: Message }) {
  const isOutbound = message.direction === "outbound";

  const body =
    message.content_type === "text"
      ? message.content_text
      : message.content_text
        ? message.content_text
        : `[${message.content_type}]`;

  return (
    <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-3 py-2 text-sm shadow-sm",
          isOutbound
            ? "rounded-br-sm bg-primary text-primary-foreground"
            : "rounded-bl-sm bg-muted text-foreground"
        )}
      >
        {body ? (
          <p className="whitespace-pre-wrap break-words">{body}</p>
        ) : (
          <p className="italic opacity-70">[empty]</p>
        )}
        <div
          className={cn(
            "mt-1 flex items-center justify-end gap-1 text-[10px]",
            isOutbound ? "text-primary-foreground/80" : "text-muted-foreground"
          )}
        >
          <span>{timeLabel(message.sent_at)}</span>
          {isOutbound && <StatusIcon status={message.status} />}
        </div>
      </div>
    </div>
  );
}
