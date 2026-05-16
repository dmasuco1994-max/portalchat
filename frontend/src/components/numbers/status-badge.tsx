import { Badge } from "@/components/ui/badge";
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
  created: "Created",
  connecting: "Connecting",
  connected: "Connected",
  disconnected: "Disconnected",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: NumberStatus }) {
  return <Badge variant={VARIANT_BY_STATUS[status]}>{LABEL_BY_STATUS[status]}</Badge>;
}
