import { Redirect, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { guardOperatorGroup } from '@/features/auth';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/** Groupe (operator) : cockpit + revue. Réservé aux rôles operator/admin. */
export default function OperatorLayout(): ReactNode {
  const status = useSessionStatus();
  const role = useRole();

  if (status === 'loading') {
    return (
      <Screen>
        <Loader fill />
      </Screen>
    );
  }
  const redirect = guardOperatorGroup(status, role);
  if (redirect) return <Redirect href={redirect} />;

  return (
    <Stack screenOptions={{ headerShown: true }}>
      <Stack.Screen name="cockpit" options={{ title: 'Cockpit' }} />
      <Stack.Screen name="review" options={{ title: 'Demandes à valider' }} />
    </Stack>
  );
}
