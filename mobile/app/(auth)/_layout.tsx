import { Redirect, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { guardAuthGroup } from '@/features/auth';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/** Groupe (auth) : accessible uniquement hors session. */
export default function AuthLayout(): ReactNode {
  const status = useSessionStatus();
  const role = useRole();

  if (status === 'loading') {
    return (
      <Screen>
        <Loader fill />
      </Screen>
    );
  }
  const redirect = guardAuthGroup(status, role);
  if (redirect) return <Redirect href={redirect} />;

  return <Stack screenOptions={{ headerShown: false }} />;
}
