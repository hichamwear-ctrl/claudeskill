import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { FlatList, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { MissionCard } from '@/features/missions';
import { EmptyState, ErrorState, Loader, Screen, useTheme } from '@/ui';

import { useAssignedMissions } from '../hooks/useOperator';

/** OP — Missions attribuées à l'intervenant. */
export function AssignedMissionsScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const missions = useAssignedMissions();
  const catalogue = useCatalogue();

  if (missions.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (missions.isError) return <Screen><ErrorState error={missions.error} onRetry={() => missions.refetch()} /></Screen>;

  return (
    <Screen padded={false}>
      <FlatList
        data={missions.data ?? []}
        keyExtractor={(m) => m.id}
        contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md, flexGrow: 1 }}
        ListEmptyComponent={<EmptyState icon="🧰" title="Aucune mission assignée" />}
        renderItem={({ item }) => (
          <MissionCard
            item={item}
            categoryLabel={catalogue.data?.find((c) => c.id === item.category_id)?.label}
            onPress={() => router.push(routes.operatorWorkDetail(item.id))}
          />
        )}
        ItemSeparatorComponent={() => <View style={{ height: theme.spacing.xs }} />}
      />
    </Screen>
  );
}
