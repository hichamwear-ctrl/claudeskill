import { Redirect, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { routes } from '@/constants/routes';
import { useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/** Pile mission (suivi/exécution) — client comme opérateur. Requiert une session. */
export default function MissionLayout(): ReactNode {
  const status = useSessionStatus();
  if (status === 'loading') {
    return (
      <Screen>
        <Loader fill />
      </Screen>
    );
  }
  if (status === 'unauthenticated') return <Redirect href={routes.signIn} />;

  return (
    <Stack screenOptions={{ headerShown: true }}>
      <Stack.Screen name="[id]/index" options={{ title: 'Mission' }} />
      <Stack.Screen name="[id]/chat" options={{ title: 'Chat' }} />
      <Stack.Screen name="[id]/map" options={{ title: 'Suivi carte' }} />
    </Stack>
  );
}
