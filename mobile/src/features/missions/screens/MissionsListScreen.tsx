import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { FlatList, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { EmptyState, ErrorState, Loader, Screen, useTheme } from '@/ui';

import { MissionCard } from '../components/MissionCard';
import { useMyMissions } from '../hooks/useMissions';

/** C-26 — Mes missions. */
export function MissionsListScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const missions = useMyMissions();
  const catalogue = useCatalogue();

  if (missions.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (missions.isError) return <Screen><ErrorState error={missions.error} onRetry={() => missions.refetch()} /></Screen>;

  const labelFor = (categoryId: string | null) =>
    catalogue.data?.find((c) => c.id === categoryId)?.label;

  return (
    <Screen padded={false}>
      <FlatList
        data={missions.data ?? []}
        keyExtractor={(m) => m.id}
        contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md, flexGrow: 1 }}
        ListEmptyComponent={
          <EmptyState
            icon="🧾"
            title="Vous n’avez pas encore de mission"
            message="Décrivez un besoin depuis l’accueil pour commencer."
          />
        }
        renderItem={({ item }) => (
          <MissionCard
            item={item}
            categoryLabel={labelFor(item.category_id)}
            onPress={() => router.push(routes.missionDetail(item.id))}
          />
        )}
        ItemSeparatorComponent={() => <View style={{ height: theme.spacing.xs }} />}
      />
    </Screen>
  );
}
