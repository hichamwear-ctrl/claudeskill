// Design tokens extracted from the Royal Dream Events website.
export const colors = {
  bgDeep: '#0b0b22',
  bgBase: '#141248',
  bgElev: '#1b1857',
  card: '#241a63',
  cardSoft: '#2a2470',

  primary: '#7c3aed',
  primary2: '#6366f1',
  rose: '#ec4899',
  pink: '#ff5cc8',
  violet: '#a78bfa',
  blue: '#3b82f6',

  gold: '#fbbf24',
  goldBright: '#FFD700',
  goldLight: '#ffe08a',

  whatsapp: '#25D366',

  text: '#f7f8fc',
  textSoft: '#cdd3e6',
  textMuted: '#9aa3c4',

  glass: 'rgba(255,255,255,0.06)',
  glassStrong: 'rgba(255,255,255,0.10)',
  border: 'rgba(255,255,255,0.12)',
  goldBorder: 'rgba(251,191,36,0.35)',
  goldBg: 'rgba(251,191,36,0.10)',
};

// Gradients (arrays consumed by expo-linear-gradient).
export const magicGradient = ['#ff5cc8', '#a855f7', '#7c4dff'];
export const magicTextGradient = ['#ff8fd6', '#b794f6'];
export const goldGradient = ['#ffe08a', '#fbbf24'];
export const goldTextGradient = ['#ffe9a8', '#fbbf24'];
export const royalGradient = ['#1b1857', '#241a63'];
export const bgGradient = ['#0b0b22', '#141248', '#1b1857'];

export const fonts = {
  display: 'Fredoka_700Bold',
  displaySemi: 'Fredoka_600SemiBold',
  displayMed: 'Fredoka_500Medium',
  bodyReg: 'Quicksand_400Regular',
  body: 'Quicksand_500Medium',
  bodySemi: 'Quicksand_600SemiBold',
  bodyBold: 'Quicksand_700Bold',
  serif: 'PlayfairDisplay_700Bold',
  serifSemi: 'PlayfairDisplay_600SemiBold',
};

export const radius = {
  sm: 14,
  md: 20,
  lg: 28,
  xl: 34,
  pill: 999,
};

export const shadows = {
  magic: {
    shadowColor: '#b15cff',
    shadowOpacity: 0.45,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 10,
  },
  gold: {
    shadowColor: '#fbbf24',
    shadowOpacity: 0.4,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  card: {
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
};
