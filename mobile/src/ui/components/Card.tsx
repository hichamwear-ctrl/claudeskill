import type { ReactNode } from 'react';
import { View, type ViewStyle } from 'react-native';

import { useTheme } from '@/ui/theme';

export interface CardProps {
  children: ReactNode;
  tone?: 'default' | 'danger';
  style?: ViewStyle;
}

/** Conteneur de contenu : surface + bordure + rayon cohérents. */
export function Card({ children, tone = 'default', style }: CardProps): ReactNode {
  const theme = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: tone === 'danger' ? theme.colors.dangerSurface : theme.colors.surface,
          borderColor: theme.colors.border,
          borderWidth: 1,
          borderRadius: theme.radius.md,
          padding: theme.spacing.lg,
          gap: theme.spacing.sm,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}
