import type { ReactNode } from 'react';
import { View } from 'react-native';

import { useTheme, type ThemeColors } from '@/ui/theme';

import { Text } from '../primitives/Text';

export type BadgeTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger';

export interface BadgeProps {
  label: string;
  tone?: BadgeTone;
}

function toneColor(colors: ThemeColors, tone: BadgeTone): string {
  switch (tone) {
    case 'primary':
      return colors.primary;
    case 'success':
      return colors.success;
    case 'warning':
      return colors.warning;
    case 'danger':
      return colors.danger;
    case 'neutral':
    default:
      return colors.textMuted;
  }
}

/** Pastille de statut (couleur + libellé — jamais l'info par la seule couleur). */
export function Badge({ label, tone = 'neutral' }: BadgeProps): ReactNode {
  const theme = useTheme();
  const color = toneColor(theme.colors, tone);
  return (
    <View
      style={{
        alignSelf: 'flex-start',
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.xs,
        paddingHorizontal: theme.spacing.sm,
        paddingVertical: 2,
        borderRadius: theme.radius.pill,
        borderWidth: 1,
        borderColor: color,
        backgroundColor: theme.colors.surface,
      }}
    >
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
      <Text variant="caption" style={{ color }}>
        {label}
      </Text>
    </View>
  );
}
