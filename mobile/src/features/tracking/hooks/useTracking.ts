import { useMutation, useQuery } from '@tanstack/react-query';

import { getOperatorLocation, updateLocation } from '../api/tracking';

/**
 * Position de l'intervenant (repli par sondage RPC ; le live via Broadcast est
 * ajouté au module Finalisation). `refetchInterval` = suivi « quasi temps réel ».
 */
export function useOperatorLocation(missionId: string, enabled = true) {
  return useQuery({
    queryKey: ['operator-location', missionId],
    queryFn: () => getOperatorLocation(missionId),
    enabled,
    refetchInterval: 5_000,
    staleTime: 0,
  });
}

/** Émission de position (intervenant). */
export function useUpdateLocation() {
  return useMutation({
    mutationFn: (input: { lat: number; lng: number; heading?: number; speed?: number; accuracy?: number }) =>
      updateLocation(input),
  });
}
