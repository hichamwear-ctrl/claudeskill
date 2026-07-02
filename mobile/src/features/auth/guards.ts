import { routes } from '@/constants/routes';
import type { SessionStatus, UserRole } from '@/types/domain';

/**
 * Décisions de routage par rôle — FONCTIONS PURES (testables sans navigateur).
 * Rappel : ces gardes ne servent qu'à l'UX ; la sécurité réelle est côté
 * serveur (RLS + RPC). Un rôle `null` (claim absent) est traité comme `client`
 * (miroir de `current_user_role()` côté base, défaut `client`).
 */

function isOperatorRole(role: UserRole | null): boolean {
  return role === 'operator' || role === 'admin';
}

/** Destination après bootstrap (session connue). `null` = attendre (loading). */
export function resolveLanding(status: SessionStatus, role: UserRole | null): string | null {
  if (status === 'loading') return null;
  if (status === 'unauthenticated') return routes.signIn;
  return isOperatorRole(role) ? routes.operatorCockpit : routes.clientHome;
}

/** Redirection à appliquer dans le groupe (auth). `null` = rester. */
export function guardAuthGroup(status: SessionStatus, role: UserRole | null): string | null {
  if (status === 'authenticated') return resolveLanding(status, role);
  return null;
}

/** Redirection à appliquer dans le groupe (client). */
export function guardClientGroup(status: SessionStatus, role: UserRole | null): string | null {
  if (status === 'loading') return null;
  if (status === 'unauthenticated') return routes.signIn;
  if (isOperatorRole(role)) return routes.operatorCockpit;
  return null;
}

/** Redirection à appliquer dans le groupe (operator). */
export function guardOperatorGroup(status: SessionStatus, role: UserRole | null): string | null {
  if (status === 'loading') return null;
  if (status === 'unauthenticated') return routes.signIn;
  if (!isOperatorRole(role)) return routes.clientHome;
  return null;
}
