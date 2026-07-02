/**
 * Fabrique centralisée des clés React Query.
 * Toute invalidation passe par ces clés (jamais de chaîne magique en ligne),
 * ce qui garantit des invalidations sûres et cohérentes entre features.
 */
export const qk = {
  health: () => ['health'] as const,

  config: {
    all: () => ['config'] as const,
    appConfig: () => ['config', 'app_config'] as const,
    catalogue: () => ['config', 'catalogue'] as const,
    questions: (setId: string) => ['config', 'questions', setId] as const,
    contentStrings: (locale: string) => ['config', 'content_strings', locale] as const,
  },

  missions: {
    all: () => ['missions'] as const,
    list: (scope: string) => ['missions', 'list', scope] as const,
    overview: (missionId: string) => ['missions', 'overview', missionId] as const,
  },

  review: {
    queue: () => ['review', 'queue'] as const,
  },

  chat: {
    messages: (missionId: string) => ['chat', 'messages', missionId] as const,
  },

  notifications: {
    list: () => ['notifications', 'list'] as const,
    unreadCount: () => ['notifications', 'unread'] as const,
  },

  profile: {
    me: () => ['profile', 'me'] as const,
    addresses: () => ['profile', 'addresses'] as const,
  },
} as const;
