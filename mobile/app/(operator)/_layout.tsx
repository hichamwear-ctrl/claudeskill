import { Redirect, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { guardOperatorGroup } from '@/features/auth';
import { ConfigBootstrap } from '@/features/config';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/** Groupe (operator) : cockpit + revue + exécution. Rôles operator/admin. */
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
    <>
      <ConfigBootstrap />
      <Stack screenOptions={{ headerShown: true }}>
        <Stack.Screen name="cockpit" options={{ title: 'Cockpit' }} />
        <Stack.Screen name="review/index" options={{ title: 'Demandes à valider' }} />
        <Stack.Screen name="review/[id]" options={{ title: 'Demande' }} />
        <Stack.Screen name="work/index" options={{ title: 'Missions assignées' }} />
        <Stack.Screen name="work/[id]" options={{ title: 'Mission en cours' }} />
      </Stack>
    </>
  );
}
