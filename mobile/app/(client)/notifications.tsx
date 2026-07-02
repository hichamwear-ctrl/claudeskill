import type { ReactNode } from 'react';

import { EmptyState, Screen } from '@/ui';

/** C-28 (shell) — Notifications. Liste in-app au module Notifications. */
export default function Notifications(): ReactNode {
  return (
    <Screen padded={false}>
      <EmptyState icon="🔔" title="Aucune notification" message="Vous serez informé ici des évolutions de vos missions." />
    </Screen>
  );
}
