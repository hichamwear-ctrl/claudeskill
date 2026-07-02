import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { FlatList } from 'react-native';

import { routes } from '@/constants/routes';
import { formatDateTime } from '@/lib/format';
import { Badge, Divider, EmptyState, ErrorState, ListItem, Loader, Screen } from '@/ui';

import { useReviewQueue } from '../hooks/useReview';

/** OP-04 — File des demandes à valider (temps réel). */
export function ReviewQueueScreen(): ReactNode {
  const router = useRouter();
  const queue = useReviewQueue();

  if (queue.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (queue.isError) return <Screen><ErrorState error={queue.error} onRetry={() => queue.refetch()} /></Screen>;

  return (
    <Screen padded={false}>
      <FlatList
        data={queue.data ?? []}
        keyExtractor={(q) => q.mission_id}
        ItemSeparatorComponent={Divider}
        ListEmptyComponent={<EmptyState icon="📋" title="Aucune demande à valider" />}
        renderItem={({ item }) => (
          <ListItem
            title={item.category_label ?? 'Demande'}
            subtitle={`${item.client_name ?? 'Client'} · ${formatDateTime(item.submitted_at)}`}
            right={item.review_claimed_by ? <Badge label="En cours" tone="warning" /> : undefined}
            onPress={() => router.push(routes.operatorReviewDetail(item.mission_id))}
          />
        )}
      />
    </Screen>
  );
}
