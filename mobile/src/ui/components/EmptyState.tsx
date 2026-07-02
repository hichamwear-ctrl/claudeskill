import type { ReactNode } from 'react';
import { View } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Button } from '../primitives/Button';
import { Text } from '../primitives/Text';

export interface EmptyStateProps {
  /** Emoji/glyphe illustratif (icônes dédiées ajoutées plus tard). */
  icon?: string;
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

/** État vide standard : illustration + message + CTA (UX_SPEC §9). */
export function EmptyState({ icon = '📭', title, message, actionLabel, onAction }: EmptyStateProps): ReactNode {
  const theme = useTheme();
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: theme.spacing.sm, padding: theme.spacing.xl }}>
      <Text variant="title">{icon}</Text>
      <Text variant="heading" style={{ textAlign: 'center' }}>
        {title}
      </Text>
      {message ? (
        <Text color="textMuted" style={{ textAlign: 'center' }}>
          {message}
        </Text>
      ) : null}
      {actionLabel && onAction ? (
        <View style={{ marginTop: theme.spacing.md, alignSelf: 'stretch' }}>
          <Button label={actionLabel} variant="secondary" onPress={onAction} />
        </View>
      ) : null}
    </View>
  );
}
