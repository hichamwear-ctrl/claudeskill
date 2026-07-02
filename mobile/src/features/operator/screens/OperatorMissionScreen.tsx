import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, type ReactNode } from 'react';
import { ScrollView, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { MissionTimeline, StatusBadge, isTrackingStatus, missionStatusLabel, useMissionOverview, useMissionStatusRealtime } from '@/features/missions';
import { useCapturePayment } from '@/features/payments';
import { useLocationBroadcaster } from '@/features/tracking';
import { useUserId } from '@/hooks/useSession';
import { toUxError } from '@/lib/errorCatalog';
import { pickAndUploadImage } from '@/services/storage/upload';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, ErrorState, Loader, Screen, Text, useTheme } from '@/ui';

import { useTransitionMission } from '../hooks/useOperator';
import { nextSteps } from '../steps';

/** OP-06/07/08 — Mission en cours : étapes, GPS, capture, chat. */
export function OperatorMissionScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useUserId();
  useMissionStatusRealtime(id);
  const overview = useMissionOverview(id);
  const catalogue = useCatalogue();
  const transition = useTransitionMission(id);
  const capture = useCapturePayment(id);
  const showToast = useUiStore((s) => s.showToast);
  const [sharing, setSharing] = useState(false);

  const status = overview.data?.mission.status;
  useLocationBroadcaster(sharing && status !== undefined && isTrackingStatus(status));

  if (overview.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (overview.isError) return <Screen><ErrorState error={overview.error} onRetry={() => overview.refetch()} /></Screen>;

  const m = overview.data!.mission;
  const categoryLabel = catalogue.data?.find((c) => c.id === m.category_id)?.label ?? 'Mission';
  const steps = nextSteps(m.status);

  const doTransition = async (to: Parameters<typeof missionStatusLabel>[0]) => {
    try {
      await transition.mutateAsync({ to });
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  const doCapture = async () => {
    try {
      const proofPath = await pickAndUploadImage({ bucket: 'mission-proofs', pathPrefix: `${userId}/${id}` });
      if (!proofPath) return; // annulé
      await capture.mutateAsync({ proofPath });
      showToast('success', 'Mission clôturée (capture simulée).');
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: theme.spacing.lg, paddingBottom: theme.spacing.xl }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text variant="title">{categoryLabel}</Text>
          <StatusBadge status={m.status} />
        </View>

        {m.dropoff_address ? (
          <Card>
            <Text variant="caption" color="textMuted">Adresse</Text>
            <Text>{m.dropoff_address}</Text>
          </Card>
        ) : null}

        {steps.length > 0 ? (
          <Card>
            <Text variant="heading">Étape suivante</Text>
            {steps.map((to) => (
              <Button key={to} label={missionStatusLabel(to)} onPress={() => doTransition(to)} loading={transition.isPending} />
            ))}
          </Card>
        ) : null}

        {m.status === 'in_progress' ? (
          <Card>
            <Text variant="heading">Clôture</Text>
            <Text color="textMuted">Ajoutez la preuve (ticket) puis clôturez.</Text>
            <Button label="Preuve + Clôturer (capture)" onPress={doCapture} loading={capture.isPending} />
          </Card>
        ) : null}

        {isTrackingStatus(m.status) ? (
          <Button
            label={sharing ? 'Arrêter le partage de position' : 'Partager ma position'}
            variant={sharing ? 'destructive' : 'secondary'}
            onPress={() => setSharing((s) => !s)}
          />
        ) : null}

        <Button label="Ouvrir le chat" variant="secondary" onPress={() => router.push(routes.missionChat(id))} />

        <MissionTimeline events={overview.data!.events} />
      </ScrollView>
    </Screen>
  );
}
