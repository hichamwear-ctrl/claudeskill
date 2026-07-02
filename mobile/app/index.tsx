import { Redirect } from 'expo-router';
import type { ReactNode } from 'react';

import { resolveLanding } from '@/features/auth';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/**
 * Bootstrap : redirige selon la session et le rôle (`user_role`).
 * - loading → splash
 * - non authentifié → /sign-in
 * - client → /home · operator|admin → /cockpit
 */
export default function Index(): ReactNode {
  const status = useSessionStatus();
  const role = useRole();
  const target = resolveLanding(status, role);

  if (!target) {
    return (
      <Screen>
        <Loader fill label="Démarrage…" />
      </Screen>
    );
  }
  return <Redirect href={target} />;
}
