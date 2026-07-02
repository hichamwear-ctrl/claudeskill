import type { ReactNode } from 'react';

import { EmptyState, Screen } from '@/ui';

/** OP-04 (shell) — Demandes à valider. File `operator_queue` au module Cockpit. */
export default function Review(): ReactNode {
  return (
    <Screen padded={false}>
      <EmptyState icon="📋" title="Aucune demande à valider" message="Les nouvelles demandes à examiner apparaîtront ici." />
    </Screen>
  );
}
