import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { NumberStatus } from "@/lib/api/types";

const VARIANT_BY_STATUS: Record<
  NumberStatus,
  React.ComponentProps<typeof Badge>["variant"]
> = {
  created: "secondary",
  connecting: "warning",
  connected: "success",
  disconnected: "warning",
  failed: "destructive",
};

const LABEL_BY_STATUS: Record<NumberStatus, string> = {
  created: "Pendiente",
  connecting: "Conectando",
  connected: "Conectado",
  disconnected: "Desconectado",
  failed: "Falló",
};

const DOT_COLOR_BY_STATUS: Record<NumberStatus, string> = {
  created: "bg-muted-foreground/60",
  connecting: "bg-amber-500",
  connected: "bg-emerald-500",
  disconnected: "bg-amber-500",
  failed: "bg-destructive",
};

interface Props {
  status: NumberStatus;
  /** When true, render a leading pulsing dot before the label (for live status). */
  pulse?: boolean;
}

export function StatusBadge({ status, pulse = false }: Props) {
  return (
    <Badge
      variant={VARIANT_BY_STATUS[status]}
      className="inline-flex items-center gap-1.5"
    >
      {pulse && (
        <span className="relative inline-flex size-1.5">
          <span
            className={cn(
              "absolute inline-flex size-full rounded-full opacity-75",
              DOT_COLOR_BY_STATUS[status],
              status === "connected" || status === "connecting"
                ? "pulse-dot"
                : ""
            )}
          />
          <span
            className={cn(
              "relative inline-flex size-1.5 rounded-full",
              DOT_COLOR_BY_STATUS[status]
            )}
          />
        </span>
      )}
      <span>{LABEL_BY_STATUS[status]}</span>
    </Badge>
  );
}
