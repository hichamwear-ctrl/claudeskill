import { Redirect, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { routes } from '@/constants/routes';
import { useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/** Pile de création de demande (au-dessus des onglets). Requiert une session. */
export default function RequestLayout(): ReactNode {
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
      <Stack.Screen name="[conversationId]/index" options={{ title: 'Votre demande' }} />
      <Stack.Screen name="[conversationId]/summary" options={{ title: 'Récapitulatif' }} />
    </Stack>
  );
}
