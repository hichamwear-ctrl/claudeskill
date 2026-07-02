import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, type ReactNode } from 'react';
import { ScrollView, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { useCurrentLocation } from '@/hooks/useCurrentLocation';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Banner, Button, Card, Divider, ErrorState, Loader, Screen, Text, useTheme } from '@/ui';

import { PriceBreakdown } from '../components/PriceBreakdown';
import { useConverse, useEstimatePrice, useSubmitRequest, useZoneCheck } from '../hooks/useIntake';
import { useIntakeStore } from '../store';
import type { AnswerValue, DossierEntry } from '../types';

function formatAnswer(value: AnswerValue): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

/** C-13 — Récapitulatif : dossier + couverture/estimation, puis envoi. */
export function SummaryScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const { conversationId } = useLocalSearchParams<{ conversationId: string }>();

  const turn = useIntakeStore((s) => s.turn);
  const setTurn = useIntakeStore((s) => s.setTurn);
  const reset = useIntakeStore((s) => s.reset);
  const converse = useConverse();
  const submit = useSubmitRequest();
  const catalogue = useCatalogue();
  const showToast = useUiStore((s) => s.showToast);

  const dossier = turn?.conversationId === conversationId ? turn.summary : null;
  const category = catalogue.data?.find((c) => c.slug === dossier?.classification) ?? null;

  const location = useCurrentLocation(Boolean(dossier));
  const zone = useZoneCheck(location.coords);
  const estimate = useEstimatePrice(category?.id ?? null, location.coords);

  useEffect(() => {
    if (!dossier && conversationId) {
      converse
        .mutateAsync({ conversation_id: conversationId })
        .then(setTurn)
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dossier, conversationId]);

  const onSubmit = async () => {
    try {
      await submit.mutateAsync(conversationId);
      showToast('success', 'Demande envoyée. En attente de validation.');
      reset();
      router.replace(routes.clientMissions);
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  if (!dossier) {
    if (converse.isError) return <Screen><ErrorState error={converse.error} onRetry={() => router.back()} /></Screen>;
    return <Screen><Loader fill label="Préparation du récapitulatif…" /></Screen>;
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: theme.spacing.lg, paddingBottom: theme.spacing.xl }}>
        <Text variant="title">Récapitulatif</Text>

        <Card>
          {dossier.entries.length === 0 ? (
            <Text color="textMuted">Aucune information saisie.</Text>
          ) : (
            dossier.entries.map((entry: DossierEntry, i) => (
              <View key={entry.key}>
                {i > 0 ? <Divider /> : null}
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: theme.spacing.md, paddingVertical: theme.spacing.xs }}>
                  <Text color="textMuted" style={{ flex: 1 }}>
                    {entry.label}
                  </Text>
                  <Text style={{ flex: 1, textAlign: 'right' }}>{formatAnswer(entry.value)}</Text>
                </View>
              </View>
            ))
          )}
        </Card>

        <ZoneSection status={location.status} covered={zone.data?.covered} open={zone.data?.open} loading={zone.isLoading} />

        {estimate.isLoading ? (
          <Loader label="Estimation…" />
        ) : estimate.data ? (
          <PriceBreakdown estimate={estimate.data} />
        ) : null}

        <Button label="Envoyer la demande" onPress={onSubmit} loading={submit.isPending} />
        <Text variant="caption" color="textMuted" style={{ textAlign: 'center' }}>
          Votre demande sera validée par un opérateur avant tout paiement.
        </Text>
      </ScrollView>
    </Screen>
  );
}

function ZoneSection({
  status,
  covered,
  open,
  loading,
}: {
  status: ReturnType<typeof useCurrentLocation>['status'];
  covered?: boolean;
  open?: boolean;
  loading: boolean;
}): ReactNode {
  if (status === 'denied' || status === 'error') {
    return <Banner tone="info" message="Activez la localisation pour l’estimation et la couverture." />;
  }
  if (status === 'loading' || loading) return <Loader label="Vérification de la zone…" />;
  if (covered === false) return <Banner tone="warning" message="Zone pas encore couverte." />;
  if (covered && open === false) return <Banner tone="warning" message="Service actuellement fermé (hors horaires)." />;
  if (covered && open) return <Banner tone="success" message="Zone couverte et service ouvert." />;
  return null;
}
