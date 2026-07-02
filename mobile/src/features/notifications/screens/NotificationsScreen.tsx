import { useRouter, type Href } from 'expo-router';
import type { ReactNode } from 'react';
import { FlatList, View } from 'react-native';

import { formatDateTime } from '@/lib/format';
import { Button, Divider, EmptyState, ErrorState, ListItem, Loader, Screen, useTheme } from '@/ui';

import { useMarkAllRead, useMarkNotificationRead, useNotifications } from '../hooks/useNotifications';

/** C-28 — Notifications in-app (liste + accusés de lecture + deep-link). */
export function NotificationsScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const query = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllRead();

  if (query.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (query.isError) return <Screen><ErrorState error={query.error} onRetry={() => query.refetch()} /></Screen>;

  const data = query.data ?? [];
  const hasUnread = data.some((n) => n.read_at === null);

  return (
    <Screen padded={false}>
      {hasUnread ? (
        <View style={{ padding: theme.spacing.md }}>
          <Button label="Tout marquer comme lu" variant="ghost" onPress={() => markAll.mutate()} loading={markAll.isPending} />
        </View>
      ) : null}
      <FlatList
        data={data}
        keyExtractor={(n) => n.id}
        ItemSeparatorComponent={Divider}
        ListEmptyComponent={<EmptyState icon="🔔" title="Aucune notification" />}
        renderItem={({ item }) => (
          <ListItem
            title={item.title}
            subtitle={`${item.body ?? ''}${item.body ? ' · ' : ''}${formatDateTime(item.created_at)}`}
            left={
              <View
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: item.read_at === null ? theme.colors.primary : 'transparent',
                }}
              />
            }
            onPress={() => {
              if (item.read_at === null) markRead.mutate(item.id);
              if (item.deep_link) router.push(item.deep_link as Href);
            }}
          />
        )}
      />
    </Screen>
  );
}
