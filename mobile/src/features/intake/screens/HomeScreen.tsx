import { useRouter } from 'expo-router';
import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { routes } from '@/constants/routes';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, Input, Screen, Text, useTheme } from '@/ui';

import { useConverse } from '../hooks/useIntake';
import { useIntakeStore } from '../store';

/** C-07 — « De quoi avez-vous besoin ? ». Saisie libre → démarre la conversation. */
export function HomeScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const converse = useConverse();
  const setTurn = useIntakeStore((s) => s.setTurn);
  const showToast = useUiStore((s) => s.showToast);
  const [message, setMessage] = useState('');

  const start = async () => {
    try {
      const turn = await converse.mutateAsync({ message: message.trim(), locale: 'fr' });
      setTurn(turn);
      router.push(routes.requestConversation(turn.conversationId));
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  return (
    <Screen>
      <View style={{ gap: theme.spacing.lg }}>
        <Text variant="title">De quoi avez-vous besoin aujourd’hui ?</Text>
        <Card>
          <Input
            placeholder="Ex. : j’ai oublié du lait, mon pneu est crevé…"
            value={message}
            onChangeText={setMessage}
            multiline
            style={{ minHeight: 96, paddingTop: theme.spacing.sm }}
          />
          <Button
            label="Continuer"
            onPress={start}
            loading={converse.isPending}
            disabled={message.trim().length === 0}
          />
        </Card>
        <Text variant="caption" color="textMuted">
          Décrivez librement votre besoin : nous vous poserons les bonnes questions.
        </Text>
      </View>
    </Screen>
  );
}
