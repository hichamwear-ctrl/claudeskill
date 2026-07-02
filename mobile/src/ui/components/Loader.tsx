import type { ReactNode } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from '../primitives/Text';

export interface LoaderProps {
  label?: string;
  /** Centre le loader dans tout l'espace disponible. */
  fill?: boolean;
}

/** Indicateur de chargement (jamais en plein écran hors splash — UX_SPEC §2). */
export function Loader({ label, fill = false }: LoaderProps): ReactNode {
  const theme = useTheme();
  return (
    <View
      style={{
        flex: fill ? 1 : undefined,
        alignItems: 'center',
        justifyContent: 'center',
        gap: theme.spacing.sm,
        padding: theme.spacing.lg,
      }}
    >
      <ActivityIndicator color={theme.colors.primary} />
      {label ? (
        <Text variant="caption" color="textMuted">
          {label}
        </Text>
      ) : null}
    </View>
  );
}
