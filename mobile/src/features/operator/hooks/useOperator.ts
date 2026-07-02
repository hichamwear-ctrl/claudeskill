import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { qk } from '@/constants/queryKeys';
import { useUserId } from '@/hooks/useSession';
import type { MissionStatus } from '@/types/domain';

import { fetchAssignedMissions, transitionMission } from '../api/operator';

/** Missions attribuées à l'intervenant courant. */
export function useAssignedMissions() {
  const userId = useUserId();
  return useQuery({
    queryKey: qk.missions.list('operator'),
    queryFn: () => fetchAssignedMissions(userId as string),
    enabled: Boolean(userId),
    staleTime: 15_000,
  });
}

/** Transition d'exécution + rafraîchissement du détail et de la liste. */
export function useTransitionMission(missionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { to: MissionStatus; reason?: string }) =>
      transitionMission(missionId, input.to, input.reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.missions.overview(missionId) });
      void queryClient.invalidateQueries({ queryKey: qk.missions.list('operator') });
    },
  });
}
