import type { MissionStatus } from '@/types/domain';
import type { BadgeTone } from '@/ui';

/** Libellé FR d'un statut de mission (data-neutre, mappé depuis l'enum). */
export function missionStatusLabel(status: MissionStatus): string {
  const map: Record<MissionStatus, string> = {
    created: 'Brouillon',
    pending_review: 'En validation',
    needs_information: 'Infos demandées',
    rejected: 'Refusée',
    accepted: 'Acceptée',
    assigned: 'Attribuée',
    searching: 'Recherche',
    shopping: 'Achats en cours',
    preparing: 'Préparation',
    en_route: 'En route',
    arrived: 'Sur place',
    in_progress: 'En cours',
    completed: 'Terminée',
    rated: 'Notée',
    cancelled: 'Annulée',
    failed: 'Échec',
  };
  return map[status];
}

/** Couleur sémantique associée à un statut (statut = couleur + libellé). */
export function missionStatusTone(status: MissionStatus): BadgeTone {
  switch (status) {
    case 'rejected':
    case 'failed':
      return 'danger';
    case 'pending_review':
    case 'needs_information':
      return 'warning';
    case 'accepted':
    case 'completed':
    case 'rated':
      return 'success';
    case 'created':
    case 'cancelled':
      return 'neutral';
    default:
      return 'primary';
  }
}

/** Étapes d'exécution où une carte de suivi live est pertinente. */
export function isTrackingStatus(status: MissionStatus): boolean {
  return ['assigned', 'shopping', 'preparing', 'en_route', 'arrived', 'in_progress'].includes(status);
}
