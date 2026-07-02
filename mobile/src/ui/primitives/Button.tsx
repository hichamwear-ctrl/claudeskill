import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, type PressableProps } from 'react-native';

import { useTheme, type Theme } from '@/ui/theme';

import { Text } from './Text';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';

export interface ButtonProps extends Omit<PressableProps, 'style' | 'children'> {
  label: string;
  variant?: ButtonVariant;
  loading?: boolean;
}

interface VariantStyle {
  background: string;
  border: string;
  text: string;
}

function variantStyle(theme: Theme, variant: ButtonVariant): VariantStyle {
  switch (variant) {
    case 'secondary':
      return { background: theme.colors.surfaceMuted, border: theme.colors.border, text: theme.colors.text };
    case 'ghost':
      return { background: 'transparent', border: 'transparent', text: theme.colors.primary };
    case 'destructive':
      return { background: theme.colors.danger, border: theme.colors.danger, text: theme.colors.primaryText };
    case 'primary':
    default:
      return { background: theme.colors.primary, border: theme.colors.primary, text: theme.colors.primaryText };
  }
}

/** Bouton d'action (cible ≥ 48 px, état chargement/désactivé, 4 variantes). */
export function Button({
  label,
  variant = 'primary',
  loading = false,
  disabled,
  ...rest
}: ButtonProps): ReactNode {
  const theme = useTheme();
  const v = variantStyle(theme, variant);
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
        backgroundColor: v.background,
        borderWidth: 1,
        borderColor: v.border,
      })}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={v.text} />
      ) : (
        <Text variant="button" style={{ color: v.text }}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}
