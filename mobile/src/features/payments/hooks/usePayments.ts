import { useMutation, useQueryClient } from '@tanstack/react-query';

import { qk } from '@/constants/queryKeys';

import { authorizePayment, capturePayment } from '../api/payments';

/** Autorisation de paiement (mock) + rafraîchissement du détail/liste. */
export function useAuthorizePayment(missionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => authorizePayment(missionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.missions.overview(missionId) });
      void queryClient.invalidateQueries({ queryKey: qk.missions.list('client') });
    },
  });
}

/** Capture de paiement (mock, opérateur) + rafraîchissement du détail. */
export function useCapturePayment(missionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { proofPath: string; amountFinal?: number; advanceActual?: number }) =>
      capturePayment({ missionId, ...input }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.missions.overview(missionId) });
    },
  });
}
