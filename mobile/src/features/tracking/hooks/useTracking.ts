import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Location from 'expo-location';
import { useEffect } from 'react';

import { channels } from '@/constants/channels';
import { acquireChannel, releaseChannel, useRealtimeChannel } from '@/services/realtime';

import { getOperatorLocation, updateLocation, type OperatorLocation } from '../api/tracking';

const LOCATION_EVENT = 'location';

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
 * Diffuse la position de l'intervenant tant que `active` (mission en cours) :
 * persiste (RPC `update_location`) ET émet en Broadcast sur
 * `mission:{id}:location` pour le suivi live du client. Foreground uniquement,
 * arrêt au démontage / à la désactivation (vie privée).
 */
export function useLocationBroadcaster(missionId: string, active: boolean): void {
  const update = useUpdateLocation();
  useEffect(() => {
    if (!active) return;
    const topic = channels.missionLocation(missionId);
    const channel = acquireChannel(topic, () => {});
    let sub: Location.LocationSubscription | undefined;

    void (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;
      sub = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 20 },
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          const heading = pos.coords.heading ?? undefined;
          const speed = pos.coords.speed ?? undefined;
          const accuracy = pos.coords.accuracy ?? undefined;
          update.mutate({ lat, lng, heading, speed, accuracy });
          const payload: OperatorLocation = {
            lat,
            lng,
            heading: heading ?? null,
            speed: speed ?? null,
            accuracy: accuracy ?? null,
          };
          void channel.send({ type: 'broadcast', event: LOCATION_EVENT, payload });
        },
      );
    })();

    return () => {
      sub?.remove();
      releaseChannel(topic);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId, active]);
}

/**
 * Réception live de la position (Broadcast) côté client : met à jour le cache
 * de `useOperatorLocation` (le sondage RPC sert de repli).
 */
export function useOperatorLocationLive(missionId: string): void {
  const queryClient = useQueryClient();
  useRealtimeChannel(
    channels.missionLocation(missionId),
    (channel) => {
      channel.on('broadcast', { event: LOCATION_EVENT }, (message) => {
        queryClient.setQueryData(['operator-location', missionId], message.payload as OperatorLocation);
      });
    },
    [missionId],
  );
}
