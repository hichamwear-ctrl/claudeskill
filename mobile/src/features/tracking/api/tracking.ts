import { callRpc } from '@/services/api';

export interface OperatorLocation {
  lat: number;
  lng: number;
  heading: number | null;
  speed: number | null;
  accuracy: number | null;
}

/** Dernière position de l'intervenant (null hors mission active). */
export async function getOperatorLocation(missionId: string): Promise<OperatorLocation | null> {
  const data = await callRpc('get_operator_location', { p_mission_id: missionId });
  return data as unknown as OperatorLocation | null;
}

/** Émission de position (intervenant assigné, mission active). */
export function updateLocation(input: {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  accuracy?: number;
}): Promise<unknown> {
  return callRpc('update_location', {
    p_lat: input.lat,
    p_lng: input.lng,
    p_heading: input.heading,
    p_speed: input.speed,
    p_accuracy: input.accuracy,
  });
}
