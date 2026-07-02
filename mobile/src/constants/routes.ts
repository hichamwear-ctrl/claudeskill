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

  // Intake (création de demande)
  requestConversation: (id: string) => `/request/${id}`,
  requestSummary: (id: string) => `/request/${id}/summary`,

  // Mission (suivi / exécution)
  missionDetail: (id: string) => `/mission/${id}`,
  missionChat: (id: string) => `/mission/${id}/chat`,
  missionMap: (id: string) => `/mission/${id}/map`,

  // Opérateur
  operatorCockpit: '/cockpit',
  operatorReview: '/review',
  operatorReviewDetail: (id: string) => `/review/${id}`,
  operatorWork: '/work',
  operatorWorkDetail: (id: string) => `/work/${id}`,
} as const;

export type AppRoute = (typeof routes)[keyof typeof routes];
