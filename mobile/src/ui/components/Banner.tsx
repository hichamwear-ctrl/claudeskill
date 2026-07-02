import type { ReactNode } from 'react';
import { View } from 'react-native';

import { useTheme, type ThemeColors } from '@/ui/theme';

import { Text } from '../primitives/Text';

export type BannerTone = 'info' | 'success' | 'warning' | 'danger';

export interface BannerProps {
  message: string;
  tone?: BannerTone;
}

function toneColor(colors: ThemeColors, tone: BannerTone): string {
  switch (tone) {
    case 'success':
      return colors.success;
    case 'warning':
      return colors.warning;
    case 'danger':
      return colors.danger;
    case 'info':
    default:
      return colors.primary;
  }
}

/** Bannière persistante (hors-ligne, info d'écran) — UX_SPEC §2. */
export function Banner({ message, tone = 'info' }: BannerProps): ReactNode {
  const theme = useTheme();
  const color = toneColor(theme.colors, tone);
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.sm,
        paddingHorizontal: theme.spacing.lg,
        paddingVertical: theme.spacing.sm,
        backgroundColor: theme.colors.surface,
        borderLeftWidth: 3,
        borderLeftColor: color,
      }}
    >
      <Text variant="caption" style={{ color, flex: 1 }}>
        {message}
      </Text>
    </View>
  );
}
