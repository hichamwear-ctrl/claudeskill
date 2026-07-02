/**
 * Design tokens — socle du Design System MAISON (pas de librairie externe).
 * Les composants ne référencent JAMAIS une couleur en dur : ils lisent le
 * thème (sémantique) → dark mode possible sans toucher les composants.
 */

export const palette = {
  white: '#FFFFFF',
  black: '#0B0F19',
  brand500: '#2563EB',
  brand600: '#1D4ED8',
  brand50: '#EFF6FF',
  gray50: '#F8FAFC',
  gray100: '#F1F5F9',
  gray200: '#E2E8F0',
  gray300: '#CBD5E1',
  gray400: '#94A3B8',
  gray500: '#64748B',
  gray700: '#334155',
  gray900: '#0F172A',
  green500: '#16A34A',
  amber500: '#D97706',
  red500: '#DC2626',
  red50: '#FEF2F2',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 16,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 24, fontWeight: '700' as const, lineHeight: 30 },
  heading: { fontSize: 18, fontWeight: '600' as const, lineHeight: 24 },
  body: { fontSize: 16, fontWeight: '400' as const, lineHeight: 22 },
  caption: { fontSize: 13, fontWeight: '400' as const, lineHeight: 18 },
  button: { fontSize: 16, fontWeight: '600' as const, lineHeight: 20 },
} as const;

export type Spacing = keyof typeof spacing;
export type Radius = keyof typeof radius;
export type TypographyVariant = keyof typeof typography;
