import { Redirect, Tabs } from 'expo-router';
import type { ReactNode } from 'react';

import { guardClientGroup } from '@/features/auth';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen, useTheme } from '@/ui';

/** Groupe (client) : barre d'onglets. Réservé au rôle client (défaut). */
export default function ClientLayout(): ReactNode {
  const theme = useTheme();
  const status = useSessionStatus();
  const role = useRole();

  if (status === 'loading') {
    return (
      <Screen>
        <Loader fill />
      </Screen>
    );
  }
  const redirect = guardClientGroup(status, role);
  if (redirect) return <Redirect href={redirect} />;

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.textMuted,
      }}
    >
      <Tabs.Screen name="home" options={{ title: 'Accueil' }} />
      <Tabs.Screen name="missions" options={{ title: 'Missions' }} />
      <Tabs.Screen name="notifications" options={{ title: 'Notifications' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profil' }} />
    </Tabs>
  );
}
