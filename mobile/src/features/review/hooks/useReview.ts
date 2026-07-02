import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { channels } from '@/constants/channels';
import { qk } from '@/constants/queryKeys';
import { useRealtimeChannel } from '@/services/realtime';

import { fetchReviewQueue, reviewAction, type ReviewActionKind } from '../api/review';

/** File de revue + abonnement temps réel (nouvelles demandes). */
export function useReviewQueue() {
  const queryClient = useQueryClient();
  useRealtimeChannel(
    channels.operatorReviewInbox(),
    (channel) => {
      channel.on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'missions', filter: 'status=eq.pending_review' },
        () => {
          void queryClient.invalidateQueries({ queryKey: qk.review.queue() });
        },
      );
    },
    [],
  );
  return useQuery({ queryKey: qk.review.queue(), queryFn: fetchReviewQueue, staleTime: 10_000 });
}

/** Action de revue (claim/accept/reject/need_info) + rafraîchissements. */
export function useReviewAction(missionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { action: ReviewActionKind; reason?: string; price?: number; etaMin?: number }) =>
      reviewAction({ missionId, ...input }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.review.queue() });
      void queryClient.invalidateQueries({ queryKey: qk.missions.overview(missionId) });
    },
  });
}
