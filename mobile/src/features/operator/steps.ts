import type { MissionStatus } from '@/types/domain';

/**
 * Étapes candidates depuis un statut d'exécution (fonction PURE, sans I/O).
 * La base valide la transition réelle selon `category_workflow` ; ceci ne fait
 * que proposer les boutons plausibles à l'intervenant.
 */
export function nextSteps(status: MissionStatus): MissionStatus[] {
  const map: Partial<Record<MissionStatus, MissionStatus[]>> = {
    assigned: ['shopping', 'en_route'],
    shopping: ['preparing', 'en_route'],
    preparing: ['en_route'],
    en_route: ['arrived'],
    arrived: ['in_progress'],
  };
  return map[status] ?? [];
}
