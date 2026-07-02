import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, type PressableProps, View } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from './Text';

export interface ButtonProps extends Omit<PressableProps, 'style' | 'children'> {
  label: string;
  variant?: 'primary' | 'secondary';
  loading?: boolean;
}

/** Bouton d'action (cible tactile ≥ 44 px, état de chargement, désactivé). */
export function Button({
  label,
  variant = 'primary',
  loading = false,
  disabled,
  ...rest
}: ButtonProps): ReactNode {
  const theme = useTheme();
  const isPrimary = variant === 'primary';
  const isDisabled = disabled || loading;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(isDisabled), busy: loading }}
      disabled={isDisabled}
      style={({ pressed }) => ({
        minHeight: 48,
        paddingHorizontal: theme.spacing.lg,
        borderRadius: theme.radius.md,
        alignItems: 'center',
        justifyContent: 'center',
        opacity: isDisabled ? 0.5 : pressed ? 0.85 : 1,
        backgroundColor: isPrimary ? theme.colors.primary : theme.colors.surfaceMuted,
        borderWidth: isPrimary ? 0 : 1,
        borderColor: theme.colors.border,
      })}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? theme.colors.primaryText : theme.colors.text} />
      ) : (
        <View>
          <Text variant="button" color={isPrimary ? 'text' : 'text'} style={{ color: isPrimary ? theme.colors.primaryText : theme.colors.text }}>
            {label}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
