"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getNotifications,
  getWorkspace,
  testNotifications,
  updateNotifications,
  updateWorkspace,
  type NotificationSettingsUpdate,
} from "@/lib/api/settings";

const NOTIF_KEY = ["settings", "notifications"];
const WORKSPACE_KEY = ["settings", "workspace"];

export function useNotifications() {
  return useQuery({ queryKey: NOTIF_KEY, queryFn: getNotifications });
}

export function useUpdateNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: NotificationSettingsUpdate) =>
      updateNotifications(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: NOTIF_KEY }),
  });
}

export function useTestNotifications() {
  return useMutation({ mutationFn: testNotifications });
}

export function useWorkspace() {
  return useQuery({ queryKey: WORKSPACE_KEY, queryFn: getWorkspace });
}

export function useUpdateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => updateWorkspace(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: WORKSPACE_KEY }),
  });
}
