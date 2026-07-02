/**
 * Noms de canaux Realtime — STABLES et centralisés (API_SPEC §7).
 * Tous les canaux `mission:{id}:*` et `operator:*` sont privés (Realtime
 * Authorization côté base : `can_access_topic` / `can_publish_topic`).
 */
export const channels = {
  missionStatus: (missionId: string) => `mission:${missionId}:status`,
  missionChat: (missionId: string) => `mission:${missionId}:chat`,
  missionTyping: (missionId: string) => `mission:${missionId}:typing`,
  missionLocation: (missionId: string) => `mission:${missionId}:location`,
  conversation: (conversationId: string) => `conversation:${conversationId}`,
  operatorReviewInbox: () => `operator:review-inbox`,
  operatorPresence: () => `operator:presence`,
} as const;
