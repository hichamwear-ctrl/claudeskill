import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { ReactNode } from 'react';

import { AppProviders } from '@/providers/AppProviders';

/**
 * Layout racine : monte tous les providers puis la pile de navigation.
 * Le routage par rôle (auth / client / operator) sera ajouté au module M3.
 */
export default function RootLayout(): ReactNode {
  return (
    <AppProviders>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </AppProviders>
  );
}
