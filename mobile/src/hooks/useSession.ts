import { useSessionStore } from '@/stores/sessionStore';
import type { SessionStatus, UserRole } from '@/types/domain';

/** Statut de session (loading / authenticated / unauthenticated). */
export function useSessionStatus(): SessionStatus {
  return useSessionStore((s) => s.status);
}

/** Rôle applicatif courant (routage UX uniquement). */
export function useRole(): UserRole | null {
  return useSessionStore((s) => s.role);
}

/** Identifiant utilisateur courant (ou null). */
export function useUserId(): string | null {
  return useSessionStore((s) => s.userId);
}
