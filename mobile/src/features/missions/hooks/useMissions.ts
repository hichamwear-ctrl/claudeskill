import { useQuery, useQueryClient } from '@tanstack/react-query';

import { channels } from '@/constants/channels';
import { qk } from '@/constants/queryKeys';
import { useUserId } from '@/hooks/useSession';
import { useRealtimeChannel } from '@/services/realtime';

import { fetchMissionOverview, fetchMyMissions } from '../api/missions';

/** Liste des missions du client. */
export function useMyMissions() {
  const userId = useUserId();
  return useQuery({
    queryKey: qk.missions.list('client'),
    queryFn: () => fetchMyMissions(userId as string),
    enabled: Boolean(userId),
    staleTime: 15_000,
  });
}

/** Détail consolidé d'une mission. */
export function useMissionOverview(missionId: string) {
  return useQuery({
    queryKey: qk.missions.overview(missionId),
    queryFn: () => fetchMissionOverview(missionId),
    staleTime: 10_000,
  });
}

/**
 * Suivi temps réel du statut (Postgres Changes sur `missions`) : invalide le
 * détail et la liste à chaque transition — l'UI reflète le serveur sans refresh.
 */
export function useMissionStatusRealtime(missionId: string): void {
  const queryClient = useQueryClient();
  useRealtimeChannel(
    channels.missionStatus(missionId),
    (channel) => {
      channel.on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'missions', filter: `id=eq.${missionId}` },
        () => {
          void queryClient.invalidateQueries({ queryKey: qk.missions.overview(missionId) });
          void queryClient.invalidateQueries({ queryKey: qk.missions.list('client') });
        },
      );
    },
    [missionId],
  );
}
