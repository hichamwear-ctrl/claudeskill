import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { qk } from '@/constants/queryKeys';

import { fetchNotifications, markAllNotificationsRead, markNotificationRead } from '../api/notifications';

/** Liste des notifications in-app. */
export function useNotifications() {
  return useQuery({
    queryKey: qk.notifications.list(),
    queryFn: fetchNotifications,
    staleTime: 15_000,
  });
}

/** Marque une notification comme lue. */
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.notifications.list() });
    },
  });
}

/** Marque toutes les notifications comme lues. */
export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.notifications.list() });
    },
  });
}
