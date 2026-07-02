import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { channels } from '@/constants/channels';
import { qk } from '@/constants/queryKeys';
import { useUserId } from '@/hooks/useSession';
import { useRealtimeChannel } from '@/services/realtime';

import { fetchMessages, markMessagesRead, sendMessage } from '../api/chat';

/**
 * Messages d'une mission + abonnement temps réel (Postgres Changes sur
 * `messages`) : tout nouvel INSERT invalide la liste → affichage immédiat.
 */
export function useMessages(missionId: string) {
  const queryClient = useQueryClient();

  useRealtimeChannel(
    channels.missionChat(missionId),
    (channel) => {
      channel.on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'messages', filter: `mission_id=eq.${missionId}` },
        () => {
          void queryClient.invalidateQueries({ queryKey: qk.chat.messages(missionId) });
        },
      );
    },
    [missionId],
  );

  return useQuery({
    queryKey: qk.chat.messages(missionId),
    queryFn: () => fetchMessages(missionId),
    staleTime: 5_000,
  });
}

/** Envoi d'un message. */
export function useSendMessage(missionId: string) {
  const userId = useUserId();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => sendMessage({ missionId, senderId: userId as string, body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.chat.messages(missionId) });
    },
  });
}

/** Marque les messages comme lus (à l'ouverture du chat). */
export function useMarkMessagesRead(missionId: string) {
  return useMutation({ mutationFn: () => markMessagesRead(missionId) });
}
