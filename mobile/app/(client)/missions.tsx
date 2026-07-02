import type { ReactNode } from 'react';

import { EmptyState, Screen } from '@/ui';

/** C-26 (shell) — Mes missions. Liste réelle au module Missions. */
export default function Missions(): ReactNode {
  return (
    <Screen padded={false}>
      <EmptyState icon="🧾" title="Vous n’avez pas encore de mission" message="Vos demandes et missions apparaîtront ici." />
    </Screen>
  );
}
