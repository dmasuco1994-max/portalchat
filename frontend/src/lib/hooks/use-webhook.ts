"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  listWebhookDeliveries,
  updateWebhookConfig,
} from "@/lib/api/webhooks";
import type { WebhookConfigUpdate } from "@/lib/api/types";

export function useWebhookDeliveries(numberId: string) {
  return useQuery({
    queryKey: ["numbers", numberId, "webhook-deliveries"],
    queryFn: () => listWebhookDeliveries(numberId),
    enabled: !!numberId,
    refetchInterval: 10000,
  });
}

export function useUpdateWebhookConfig(numberId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: WebhookConfigUpdate) =>
      updateWebhookConfig(numberId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["numbers", numberId] });
      qc.invalidateQueries({ queryKey: ["numbers"] });
    },
  });
}
