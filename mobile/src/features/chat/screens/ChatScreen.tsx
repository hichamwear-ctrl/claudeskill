import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState, type ReactNode } from 'react';
import { FlatList, KeyboardAvoidingView, Platform, View } from 'react-native';

import { useUserId } from '@/hooks/useSession';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import type { Message } from '@/types/domain';
import { Button, EmptyState, ErrorState, Input, Loader, Screen, Text, useTheme } from '@/ui';

import { useMarkMessagesRead, useMessages, useSendMessage } from '../hooks/useChat';

/** C-20 / OP-10 — Chat d'exécution (temps réel). */
export function ChatScreen(): ReactNode {
  const theme = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useUserId();
  const messages = useMessages(id);
  const send = useSendMessage(id);
  const markRead = useMarkMessagesRead(id);
  const showToast = useUiStore((s) => s.showToast);
  const [draft, setDraft] = useState('');

  useEffect(() => {
    markRead.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onSend = async () => {
    const body = draft.trim();
    if (!body) return;
    setDraft('');
    try {
      await send.mutateAsync(body);
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  if (messages.isLoading) return <Screen><Loader fill label="Chargement du chat…" /></Screen>;
  if (messages.isError) return <Screen><ErrorState error={messages.error} onRetry={() => messages.refetch()} /></Screen>;

  return (
    <Screen padded={false}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <FlatList
          data={messages.data ?? []}
          keyExtractor={(m) => m.id}
          contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.sm, flexGrow: 1 }}
          ListEmptyComponent={<EmptyState icon="💬" title="Démarrez la conversation" />}
          renderItem={({ item }) => <Bubble message={item} mine={item.sender_id === userId} />}
        />
        <View style={{ flexDirection: 'row', gap: theme.spacing.sm, padding: theme.spacing.md, borderTopWidth: 1, borderTopColor: theme.colors.border }}>
          <View style={{ flex: 1 }}>
            <Input value={draft} onChangeText={setDraft} placeholder="Votre message…" />
          </View>
          <Button label="Envoyer" onPress={onSend} loading={send.isPending} disabled={draft.trim().length === 0} />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

function Bubble({ message, mine }: { message: Message; mine: boolean }): ReactNode {
  const theme = useTheme();
  if (message.kind === 'system') {
    return (
      <Text variant="caption" color="textMuted" style={{ textAlign: 'center' }}>
        {message.body}
      </Text>
    );
  }
  return (
    <View
      style={{
        alignSelf: mine ? 'flex-end' : 'flex-start',
        maxWidth: '80%',
        backgroundColor: mine ? theme.colors.primary : theme.colors.surface,
        borderColor: theme.colors.border,
        borderWidth: mine ? 0 : 1,
        borderRadius: theme.radius.md,
        paddingHorizontal: theme.spacing.md,
        paddingVertical: theme.spacing.sm,
      }}
    >
      <Text style={{ color: mine ? theme.colors.primaryText : theme.colors.text }}>{message.body}</Text>
    </View>
  );
}
