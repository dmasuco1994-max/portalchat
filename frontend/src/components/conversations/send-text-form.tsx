"use client";

import * as React from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useSendText } from "@/lib/hooks/use-conversations";

interface Props {
  numberId: string;
  conversationId: string;
  recipientDigits: string;
  disabled?: boolean;
  disabledReason?: string;
}

export function SendTextForm({
  numberId,
  conversationId,
  recipientDigits,
  disabled = false,
  disabledReason,
}: Props) {
  const [text, setText] = React.useState("");
  const send = useSendText(numberId, conversationId);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    try {
      await send.mutateAsync({ to: recipientDigits, text: trimmed });
      setText("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not send");
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSubmit(e);
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 border-t bg-background p-3">
      {disabled && disabledReason && (
        <p className="text-xs text-muted-foreground">{disabledReason}</p>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={disabled ? "Sending disabled" : "Type a message…"}
          rows={1}
          disabled={disabled || send.isPending}
          className="max-h-40 min-h-[44px] resize-none"
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || send.isPending || !text.trim()}
          aria-label="Send"
        >
          <Send className="size-4" />
        </Button>
      </div>
    </form>
  );
}
