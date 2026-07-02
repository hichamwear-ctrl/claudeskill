import { Text as RNText, type TextProps as RNTextProps } from 'react-native';

import { useTheme, type TypographyVariant } from '@/ui/theme';

export interface TextProps extends RNTextProps {
  variant?: TypographyVariant;
  color?: 'text' | 'textMuted' | 'primary' | 'danger' | 'success';
}

/** Texte thémé : variante typographique + couleur sémantique. */
export function Text({ variant = 'body', color = 'text', style, ...rest }: TextProps): React.ReactNode {
  const theme = useTheme();
  return (
    <RNText
      style={[theme.typography[variant], { color: theme.colors[color] }, style]}
      {...rest}
    />
  );
}
