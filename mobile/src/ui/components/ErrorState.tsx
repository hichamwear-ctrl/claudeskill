import type { ReactNode } from 'react';
import { View } from 'react-native';

import { toUxError } from '@/lib/errorCatalog';
import { useTheme } from '@/ui/theme';

import { Button } from '../primitives/Button';
import { Text } from '../primitives/Text';

export interface ErrorStateProps {
  /** Erreur brute (mappée vers un message UX rassurant) ou message direct. */
  error?: unknown;
  message?: string;
  onRetry?: () => void;
}

/** État d'erreur standard : message rassurant + bouton Réessayer (UX_SPEC §2). */
export function ErrorState({ error, message, onRetry }: ErrorStateProps): ReactNode {
  const theme = useTheme();
  const text = message ?? toUxError(error).message;
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: theme.spacing.sm, padding: theme.spacing.xl }}>
      <Text variant="heading" color="danger" style={{ textAlign: 'center' }}>
        Une erreur est survenue
      </Text>
      <Text color="textMuted" style={{ textAlign: 'center' }}>
        {text}
      </Text>
      {onRetry ? (
        <View style={{ marginTop: theme.spacing.md, alignSelf: 'stretch' }}>
          <Button label="Réessayer" onPress={onRetry} />
        </View>
      ) : null}
    </View>
  );
}
