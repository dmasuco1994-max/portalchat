"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createNumber,
  deleteNumber,
  disconnectNumber,
  getNumber,
  getNumberQr,
  getNumberStatus,
  listNumbers,
} from "@/lib/api/numbers";
import type { NumberStatus } from "@/lib/api/types";

const TERMINAL_FOR_QR: NumberStatus[] = ["connected"];

export function useNumbers() {
  return useQuery({
    queryKey: ["numbers"],
    queryFn: listNumbers,
  });
}

export function useNumber(id: string) {
  return useQuery({
    queryKey: ["numbers", id],
    queryFn: () => getNumber(id),
    enabled: !!id,
  });
}

/**
 * Poll the connection status every 3s while the number is in a transient
 * state. Stops polling once the backend reports a stable status.
 */
export function useNumberStatusPolling(id: string, currentStatus?: NumberStatus) {
  const shouldPoll =
    !!currentStatus && !["connected", "failed"].includes(currentStatus);
  return useQuery({
    queryKey: ["numbers", id, "status"],
    queryFn: () => getNumberStatus(id),
    enabled: !!id,
    refetchInterval: shouldPoll ? 3000 : false,
  });
}

/**
 * Fetch the QR code while the number is not yet connected. Polls so the QR
 * gets refreshed after Evolution rotates it (Evolution rotates every ~20s
 * on the default QRCODE_LIMIT).
 */
export function useNumberQr(id: string, currentStatus?: NumberStatus) {
  const shouldFetch =
    !!currentStatus && !TERMINAL_FOR_QR.includes(currentStatus);
  return useQuery({
    queryKey: ["numbers", id, "qr"],
    queryFn: () => getNumberQr(id),
    enabled: !!id && shouldFetch,
    refetchInterval: shouldFetch ? 15000 : false,
  });
}

export function useCreateNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createNumber,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["numbers"] });
    },
  });
}

export function useDisconnectNumber(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => disconnectNumber(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["numbers"] });
      qc.invalidateQueries({ queryKey: ["numbers", id] });
    },
  });
}

export function useDeleteNumber(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => deleteNumber(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["numbers"] });
    },
  });
}
