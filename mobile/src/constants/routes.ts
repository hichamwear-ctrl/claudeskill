/**
 * Routes de l'app (expo-router). Les segments de groupe `(auth)`/`(client)`/
 * `(operator)` n'apparaissent PAS dans l'URL : les noms d'écran sont uniques
 * entre groupes, donc les chemins sont directs.
 */
export const routes = {
  bootstrap: '/',
  health: '/health',

  // Auth
  onboarding: '/onboarding',
  signIn: '/sign-in',
  verifyOtp: '/verify-otp',
  completeProfile: '/complete-profile',

  // Client
  clientHome: '/home',
  clientMissions: '/missions',
  clientNotifications: '/notifications',
  clientProfile: '/profile',

  // Opérateur
  operatorCockpit: '/cockpit',
  operatorReview: '/review',
} as const;

export type AppRoute = (typeof routes)[keyof typeof routes];
