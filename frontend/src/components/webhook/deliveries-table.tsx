"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { WebhookDelivery, WebhookDeliveryStatus } from "@/lib/api/types";

const STATUS_VARIANT: Record<
  WebhookDeliveryStatus,
  React.ComponentProps<typeof Badge>["variant"]
> = {
  pending: "secondary",
  in_progress: "warning",
  success: "success",
  failed: "destructive",
  abandoned: "destructive",
};

function timeLabel(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function DeliveriesTable({ deliveries }: { deliveries: WebhookDelivery[] }) {
  const [expanded, setExpanded] = React.useState<string | null>(null);

  if (deliveries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Delivery history</CardTitle>
          <CardDescription>
            No outbound webhook deliveries yet for this number.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Delivery history</CardTitle>
        <CardDescription>
          Polled every 10s. Click a row for the response details.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <div className="divide-y border-y text-sm">
          {deliveries.map((d) => {
            const isOpen = expanded === d.id;
            return (
              <div key={d.id}>
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : d.id)}
                  className={cn(
                    "grid w-full grid-cols-[7rem_1fr_5rem_6rem] items-center gap-3 px-4 py-2.5 text-left hover:bg-muted/40",
                    isOpen && "bg-muted/30"
                  )}
                >
                  <Badge variant={STATUS_VARIANT[d.status]} className="justify-center">
                    {d.status}
                  </Badge>
                  <span className="truncate font-mono text-xs text-muted-foreground">
                    {d.event_type}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {d.attempts}/{d.max_attempts}
                  </span>
                  <span className="text-right text-xs text-muted-foreground">
                    {timeLabel(d.last_attempt_at ?? d.created_at)}
                  </span>
                </button>
                {isOpen && (
                  <div className="space-y-2 bg-muted/20 px-4 py-3 text-xs">
                    <p className="break-all">
                      <span className="text-muted-foreground">URL: </span>
                      <span className="font-mono">{d.target_url}</span>
                    </p>
                    {d.response_status !== null && (
                      <p>
                        <span className="text-muted-foreground">HTTP: </span>
                        <span className="font-mono">{d.response_status}</span>
                      </p>
                    )}
                    {d.response_body_excerpt && (
                      <div>
                        <p className="text-muted-foreground">Response body:</p>
                        <pre className="mt-1 max-h-40 overflow-auto rounded border bg-background p-2 font-mono">
                          {d.response_body_excerpt}
                        </pre>
                      </div>
                    )}
                    {d.error_message && (
                      <div>
                        <p className="text-muted-foreground">Error:</p>
                        <pre className="mt-1 max-h-40 overflow-auto rounded border border-destructive/40 bg-destructive/5 p-2 font-mono text-destructive">
                          {d.error_message}
                        </pre>
                      </div>
                    )}
                    {d.next_retry_at && d.status !== "success" && (
                      <p>
                        <span className="text-muted-foreground">Next retry: </span>
                        {timeLabel(d.next_retry_at)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
