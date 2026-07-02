import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from '../primitives/Text';

export interface ListItemProps {
  title: string;
  subtitle?: string;
  left?: ReactNode;
  right?: ReactNode;
  onPress?: () => void;
}

/** Ligne de liste : élément gauche optionnel, titre/sous-titre, élément droit. */
export function ListItem({ title, subtitle, left, right, onPress }: ListItemProps): ReactNode {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : undefined}
      style={({ pressed }) => ({
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.md,
        minHeight: 56,
        paddingHorizontal: theme.spacing.lg,
        paddingVertical: theme.spacing.sm,
        backgroundColor: pressed && onPress ? theme.colors.surfaceMuted : theme.colors.surface,
      })}
    >
      {left}
      <View style={{ flex: 1, gap: 2 }}>
        <Text>{title}</Text>
        {subtitle ? (
          <Text variant="caption" color="textMuted">
            {subtitle}
          </Text>
        ) : null}
      </View>
      {right}
    </Pressable>
  );
}
