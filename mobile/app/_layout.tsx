import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { ReactNode } from 'react';

import { AppProviders } from '@/providers/AppProviders';
import { OfflineBanner, ToastHost } from '@/ui';

/**
 * Layout racine : providers + pile de navigation + hôte de toasts.
 * Les groupes (auth)/(client)/(operator) appliquent leurs propres gardes de rôle.
 */
export default function RootLayout(): ReactNode {
  return (
    <AppProviders>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
      <OfflineBanner />
      <ToastHost />
    </AppProviders>
  );
}
