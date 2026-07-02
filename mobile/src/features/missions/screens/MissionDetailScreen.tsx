import { useLocalSearchParams, useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { ScrollView, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { useAuthorizePayment } from '@/features/payments';
import { toUxError } from '@/lib/errorCatalog';
import { formatMoney } from '@/lib/format';
import { useUiStore } from '@/stores/uiStore';
import { Banner, Button, Card, ErrorState, Loader, Screen, Text, useTheme } from '@/ui';

import { MissionTimeline } from '../components/MissionTimeline';
import { StatusBadge } from '../components/StatusBadge';
import { useMissionOverview, useMissionStatusRealtime } from '../hooks/useMissions';
import { isTrackingStatus } from '../status';

/** C-18 — Suivi de mission (détail + paiement + timeline + accès chat/carte). */
export function MissionDetailScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  useMissionStatusRealtime(id);
  const overview = useMissionOverview(id);
  const catalogue = useCatalogue();
  const authorize = useAuthorizePayment(id);
  const showToast = useUiStore((s) => s.showToast);

  if (overview.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (overview.isError) return <Screen><ErrorState error={overview.error} onRetry={() => overview.refetch()} /></Screen>;

  const data = overview.data!;
  const m = data.mission;
  const categoryLabel = catalogue.data?.find((c) => c.id === m.category_id)?.label ?? 'Demande';
  const canPay = m.status === 'accepted' && (!data.payment || data.payment.status === 'pending');
  const canChat = Boolean(m.operator_id) || data.unread_messages > 0;

  const onPay = async () => {
    try {
      await authorize.mutateAsync();
      showToast('success', 'Paiement autorisé (simulé). Mission attribuée.');
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

        {m.status === 'needs_information' && m.review_reason ? (
          <Banner tone="warning" message={`Infos demandées : ${m.review_reason}`} />
        ) : null}
        {m.status === 'rejected' ? (
          <Banner tone="danger" message={m.review_reason ? `Refusée : ${m.review_reason}` : 'Demande refusée.'} />
        ) : null}

        {m.dropoff_address ? (
          <Card>
            <Text variant="caption" color="textMuted">Adresse</Text>
            <Text>{m.dropoff_address}</Text>
          </Card>
        ) : null}

        {/* Paiement (gate P1 : visible seulement après acceptation) */}
        {canPay ? (
          <Card>
            <Text variant="heading">Paiement</Text>
            <Text color="textMuted">
              {m.quoted_price !== null ? `Montant : ${formatMoney(m.quoted_price)}` : 'Montant sur devis'}
            </Text>
            <Button label="Payer (simulé)" onPress={onPay} loading={authorize.isPending} />
          </Card>
        ) : data.payment ? (
          <Card>
            <Text variant="heading">Paiement</Text>
            <Text color="textMuted">Statut : {data.payment.status}</Text>
            {data.payment.amount_authorized !== null ? (
              <Text>Autorisé : {formatMoney(data.payment.amount_authorized, data.payment.currency.toUpperCase())}</Text>
            ) : null}
            {data.payment.amount_captured !== null ? (
              <Text>Capturé : {formatMoney(data.payment.amount_captured, data.payment.currency.toUpperCase())}</Text>
            ) : null}
          </Card>
        ) : null}

        <MissionTimeline events={data.events} />

        <View style={{ gap: theme.spacing.sm }}>
          {canChat ? <Button label="Ouvrir le chat" variant="secondary" onPress={() => router.push(routes.missionChat(id))} /> : null}
          {isTrackingStatus(m.status) ? (
            <Button label="Suivre sur la carte" variant="secondary" onPress={() => router.push(routes.missionMap(id))} />
          ) : null}
        </View>
      </ScrollView>
    </Screen>
  );
}
