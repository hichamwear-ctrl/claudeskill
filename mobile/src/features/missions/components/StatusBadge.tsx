import type { ReactNode } from 'react';

import type { MissionStatus } from '@/types/domain';
import { Badge } from '@/ui';

import { missionStatusLabel, missionStatusTone } from '../status';

/** Pastille de statut de mission (couleur + libellé). */
export function StatusBadge({ status }: { status: MissionStatus }): ReactNode {
  return <Badge label={missionStatusLabel(status)} tone={missionStatusTone(status)} />;
}
