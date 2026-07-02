import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ScrollView, View } from 'react-native';

import { useCatalogue } from '@/features/config';
import { useMissionOverview } from '@/features/missions';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, ErrorState, Input, Loader, Screen, Text, useTheme } from '@/ui';

import { useReviewAction } from '../hooks/useReview';

/** OP-05 — Détail demande & décision (claim + accept/reject/need_info). */
export function ReviewDetailScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const overview = useMissionOverview(id);
  const catalogue = useCatalogue();
  const action = useReviewAction(id);
  const showToast = useUiStore((s) => s.showToast);

  const [reason, setReason] = useState('');
  const [price, setPrice] = useState('');
  const [eta, setEta] = useState('');
  const claimed = useRef(false);

  // Prise en charge (claim) à l'ouverture — verrou anti double-traitement.
  useEffect(() => {
    if (claimed.current) return;
    claimed.current = true;
    action.mutateAsync({ action: 'claim' }).catch((error) => {
      showToast('error', toUxError(error).message);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (overview.isLoading) return <Screen><Loader fill label="Chargement…" /></Screen>;
  if (overview.isError) return <Screen><ErrorState error={overview.error} onRetry={() => overview.refetch()} /></Screen>;

  const m = overview.data!.mission;
  const category = catalogue.data?.find((c) => c.id === m.category_id);
  const quoteOnly = (category?.metadata as Record<string, unknown> | undefined)?.quote_only === true;
  const details = (m.details ?? {}) as Record<string, unknown>;

  const run = async (kind: 'accept' | 'reject' | 'need_info') => {
    if ((kind === 'reject' || kind === 'need_info') && !reason.trim()) {
      showToast('error', 'Un motif est requis.');
      return;
    }
    if (kind === 'accept' && quoteOnly && !price.trim()) {
      showToast('error', 'Un prix est requis pour cette catégorie.');
      return;
    }
    try {
      await action.mutateAsync({
        action: kind,
        reason: reason.trim() || undefined,
        price: kind === 'accept' && price ? Number(price) : undefined,
        etaMin: kind === 'accept' && eta ? Number(eta) : undefined,
      });
      showToast('success', 'Décision enregistrée.');
      router.back();
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: theme.spacing.lg, paddingBottom: theme.spacing.xl }}>
        <Text variant="title">{category?.label ?? 'Demande'}</Text>

        <Card>
          <Text variant="heading">Détails</Text>
          {Object.keys(details).length === 0 ? (
            <Text color="textMuted">Aucun détail structuré.</Text>
          ) : (
            Object.entries(details).map(([key, value]) => (
              <View key={key} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: theme.spacing.md }}>
                <Text color="textMuted" style={{ flex: 1 }}>{key}</Text>
                <Text style={{ flex: 1, textAlign: 'right' }}>
                  {Array.isArray(value) ? value.join(', ') : String(value)}
                </Text>
              </View>
            ))
          )}
        </Card>

        {quoteOnly ? (
          <Card>
            <Text variant="heading">Devis</Text>
            <Input label="Prix (€)" keyboardType="numeric" value={price} onChangeText={setPrice} />
            <Input label="Délai estimé (min)" keyboardType="numeric" value={eta} onChangeText={setEta} />
          </Card>
        ) : null}

        <Input label="Motif (refus / demande d’infos)" value={reason} onChangeText={setReason} multiline />

        <View style={{ gap: theme.spacing.sm }}>
          <Button label="Accepter" onPress={() => run('accept')} loading={action.isPending} />
          <Button label="Demander des infos" variant="secondary" onPress={() => run('need_info')} loading={action.isPending} />
          <Button label="Refuser" variant="destructive" onPress={() => run('reject')} loading={action.isPending} />
        </View>
      </ScrollView>
    </Screen>
  );
}
