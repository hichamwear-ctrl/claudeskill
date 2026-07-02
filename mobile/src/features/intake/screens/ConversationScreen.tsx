import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, type ReactNode } from 'react';
import { ScrollView, View } from 'react-native';

import { routes } from '@/constants/routes';
import { useCatalogue } from '@/features/config';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Banner, Button, ErrorState, Loader, Screen, Text, useTheme } from '@/ui';

import { DynamicQuestion } from '../components/DynamicQuestion';
import { useConverse } from '../hooks/useIntake';
import { useIntakeStore } from '../store';
import type { AnswerValue } from '../types';

/** C-09/C-10 — Dialogue guidé : rend la prochaine question, avance à chaque réponse. */
export function ConversationScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const { conversationId } = useLocalSearchParams<{ conversationId: string }>();
  const turn = useIntakeStore((s) => s.turn);
  const setTurn = useIntakeStore((s) => s.setTurn);
  const converse = useConverse();
  const catalogue = useCatalogue();
  const showToast = useUiStore((s) => s.showToast);

  const hydrated = turn?.conversationId === conversationId;

  const hydrate = useCallback(() => {
    if (!conversationId) return;
    converse
      .mutateAsync({ conversation_id: conversationId })
      .then(setTurn)
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => {
    if (!hydrated) hydrate();
  }, [hydrated, hydrate]);

  const answer = async (value: AnswerValue) => {
    if (!turn?.next) return;
    try {
      const next = await converse.mutateAsync({
        conversation_id: conversationId,
        answer: { key: turn.next.key, value },
      });
      setTurn(next);
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  if (!hydrated) {
    if (converse.isError) return <Screen><ErrorState error={converse.error} onRetry={hydrate} /></Screen>;
    return <Screen><Loader fill label="Chargement du dialogue…" /></Screen>;
  }

  const categoryLabel =
    catalogue.data?.find((c) => c.slug === turn.classification)?.label ?? null;

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: theme.spacing.lg, paddingBottom: theme.spacing.xl }}>
        {categoryLabel ? <Banner tone="info" message={`Besoin identifié : ${categoryLabel}`} /> : null}
        {turn.invalid.length > 0 ? (
          <Banner tone="warning" message="Certaines réponses doivent être corrigées." />
        ) : null}

        {turn.next ? (
          <DynamicQuestion question={turn.next} submitting={converse.isPending} onSubmit={answer} />
        ) : turn.canSummarize ? (
          <View style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Tout est prêt</Text>
            <Text color="textMuted">Vérifiez le récapitulatif avant d’envoyer votre demande.</Text>
            <Button
              label="Voir le récapitulatif"
              onPress={() => router.push(routes.requestSummary(conversationId))}
            />
          </View>
        ) : (
          <Text color="textMuted">Aucune question supplémentaire.</Text>
        )}
      </ScrollView>
    </Screen>
  );
}
