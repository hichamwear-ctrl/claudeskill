import { describe, expect, it } from '@jest/globals';

import type { MissionStatus } from '@/types/domain';

import { isTrackingStatus, missionStatusLabel, missionStatusTone } from '../status';

const ALL: MissionStatus[] = [
  'created', 'pending_review', 'needs_information', 'rejected', 'accepted', 'assigned',
  'searching', 'shopping', 'preparing', 'en_route', 'arrived', 'in_progress', 'completed',
  'rated', 'cancelled', 'failed',
];

describe('missionStatus mapping', () => {
  it('fournit un libellé non vide pour chaque statut', () => {
    for (const s of ALL) expect(missionStatusLabel(s).length).toBeGreaterThan(0);
  });

  it('associe les bonnes tonalités', () => {
    expect(missionStatusTone('rejected')).toBe('danger');
    expect(missionStatusTone('completed')).toBe('success');
    expect(missionStatusTone('pending_review')).toBe('warning');
    expect(missionStatusTone('in_progress')).toBe('primary');
  });

  it('identifie les statuts de suivi live', () => {
    expect(isTrackingStatus('en_route')).toBe(true);
    expect(isTrackingStatus('pending_review')).toBe(false);
    expect(isTrackingStatus('completed')).toBe(false);
  });
});
