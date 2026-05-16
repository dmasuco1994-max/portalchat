"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  listConversations,
  listMessages,
  sendText,
  type SendTextInput,
} from "@/lib/api/conversations";

export function useConversations(numberId: string) {
  return useQuery({
    queryKey: ["numbers", numberId, "conversations"],
    queryFn: () => listConversations(numberId),
    enabled: !!numberId,
    refetchInterval: 5000,
  });
}

export function useMessages(conversationId: string) {
  return useQuery({
    queryKey: ["conversations", conversationId, "messages"],
    queryFn: () => listMessages(conversationId),
    enabled: !!conversationId,
    refetchInterval: 3000,
  });
}

export function useSendText(numberId: string, conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: SendTextInput) => sendText(numberId, input),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["conversations", conversationId, "messages"],
      });
      qc.invalidateQueries({
        queryKey: ["numbers", numberId, "conversations"],
      });
    },
  });
}
