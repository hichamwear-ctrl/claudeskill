import { palette, radius, spacing, typography } from './tokens';

/** Couleurs sémantiques (indépendantes du mode clair/sombre). */
export interface ThemeColors {
  background: string;
  surface: string;
  surfaceMuted: string;
  border: string;
  text: string;
  textMuted: string;
  primary: string;
  primaryText: string;
  success: string;
  warning: string;
  danger: string;
  dangerSurface: string;
}

export interface Theme {
  mode: 'light' | 'dark';
  colors: ThemeColors;
  spacing: typeof spacing;
  radius: typeof radius;
  typography: typeof typography;
}

/** Thème CLAIR — V1 (UX_SPEC : dark ajouté ultérieurement, tokens déjà prêts). */
export const lightTheme: Theme = {
  mode: 'light',
  colors: {
    background: palette.gray50,
    surface: palette.white,
    surfaceMuted: palette.gray100,
    border: palette.gray200,
    text: palette.gray900,
    textMuted: palette.gray500,
    primary: palette.brand500,
    primaryText: palette.white,
    success: palette.green500,
    warning: palette.amber500,
    danger: palette.red500,
    dangerSurface: palette.red50,
  },
  spacing,
  radius,
  typography,
};
