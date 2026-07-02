import { useMutation, useQuery } from '@tanstack/react-query';
import * as Location from 'expo-location';
import { useEffect } from 'react';

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

/**
 * Diffuse la position de l'intervenant tant que `active` (mission en cours).
 * Foreground uniquement, s'arrête au démontage / à la désactivation (vie privée).
 */
export function useLocationBroadcaster(active: boolean): void {
  const update = useUpdateLocation();
  useEffect(() => {
    if (!active) return;
    let sub: Location.LocationSubscription | undefined;
    void (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;
      sub = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 20 },
        (pos) => {
          update.mutate({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            heading: pos.coords.heading ?? undefined,
            speed: pos.coords.speed ?? undefined,
            accuracy: pos.coords.accuracy ?? undefined,
          });
        },
      );
    })();
    return () => sub?.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);
}
