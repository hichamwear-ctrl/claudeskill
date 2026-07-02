import { callEdge } from '@/services/api';

/** Réponse de la sonde `health` (Edge Function publique). */
export interface HealthStatus {
  status: string;
  service: string;
  time: string;
}

/** Vérifie que le runtime Edge Functions répond (aucune donnée métier). */
export async function pingHealth(): Promise<HealthStatus> {
  return callEdge<HealthStatus>('health', undefined, { method: 'GET' });
}
