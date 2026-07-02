import { Redirect, Tabs } from 'expo-router';
import { Fragment, type ReactNode } from 'react';

import { guardClientGroup } from '@/features/auth';
import { ConfigBootstrap } from '@/features/config';
import { useNotifications } from '@/features/notifications';
import { useRole, useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen, useTheme } from '@/ui';

/** Groupe (client) : barre d'onglets. Réservé au rôle client (défaut). */
export default function ClientLayout(): ReactNode {
  const theme = useTheme();
  const status = useSessionStatus();
  const role = useRole();
  const notifications = useNotifications();
  const unread = (notifications.data ?? []).filter((n) => n.read_at === null).length;

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
    <Fragment>
      <ConfigBootstrap />
      <Tabs
        screenOptions={{
          headerShown: true,
          tabBarActiveTintColor: theme.colors.primary,
          tabBarInactiveTintColor: theme.colors.textMuted,
        }}
      >
        <Tabs.Screen name="home" options={{ title: 'Accueil' }} />
        <Tabs.Screen name="missions" options={{ title: 'Missions' }} />
        <Tabs.Screen
          name="notifications"
          options={{ title: 'Notifications', tabBarBadge: unread > 0 ? unread : undefined }}
        />
        <Tabs.Screen name="profile" options={{ title: 'Profil' }} />
      </Tabs>
    </Fragment>
  );
}
