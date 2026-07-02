import { forwardRef, type ReactNode } from 'react';
import { TextInput, View, type TextInputProps } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from '../primitives/Text';

export interface InputProps extends TextInputProps {
  label?: string;
  error?: string | null;
  hint?: string;
}

/**
 * Champ de saisie contrôlé et présentationnel (label + erreur + hint).
 * Se branche à React Hook Form via `Controller` (value / onChangeText / onBlur).
 */
export const Input = forwardRef<TextInput, InputProps>(function Input(
  { label, error, hint, style, ...rest },
  ref,
): ReactNode {
  const theme = useTheme();
  const hasError = Boolean(error);

  return (
    <View style={{ gap: theme.spacing.xs }}>
      {label ? (
        <Text variant="caption" color="textMuted">
          {label}
        </Text>
      ) : null}
      <TextInput
        ref={ref}
        placeholderTextColor={theme.colors.textMuted}
        style={[
          {
            minHeight: 48,
            paddingHorizontal: theme.spacing.md,
            borderRadius: theme.radius.md,
            borderWidth: 1,
            borderColor: hasError ? theme.colors.danger : theme.colors.border,
            backgroundColor: theme.colors.surface,
            color: theme.colors.text,
            fontSize: theme.typography.body.fontSize,
          },
          style,
        ]}
        {...rest}
      />
      {hasError ? (
        <Text variant="caption" color="danger">
          {error}
        </Text>
      ) : hint ? (
        <Text variant="caption" color="textMuted">
          {hint}
        </Text>
      ) : null}
    </View>
  );
});
