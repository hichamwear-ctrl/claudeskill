import type { Session } from '@supabase/supabase-js';
import { jwtDecode } from 'jwt-decode';
import { create } from 'zustand';

import type { AppJwtClaims, SessionStatus, UserRole } from '@/types/domain';

/** Décode le rôle métier (`user_role`) depuis l'access token (claim du hook). */
function decodeRole(session: Session | null): UserRole | null {
  if (!session?.access_token) return null;
  try {
    const claims = jwtDecode<AppJwtClaims>(session.access_token);
    return claims.user_role ?? null;
  } catch {
    return null;
  }
}

interface SessionStoreState {
  status: SessionStatus;
  session: Session | null;
  userId: string | null;
  /** Rôle applicatif (routage UX uniquement — la sécurité est côté serveur). */
  role: UserRole | null;
  /** Applique une session (ou `null`) : recalcule userId + rôle + statut. */
  setSession: (session: Session | null) => void;
  /** Marque le bootstrap en cours. */
  setLoading: () => void;
}

export const useSessionStore = create<SessionStoreState>((set) => ({
  status: 'loading',
  session: null,
  userId: null,
  role: null,
  setSession: (session) =>
    set({
      session,
      userId: session?.user.id ?? null,
      role: decodeRole(session),
      status: session ? 'authenticated' : 'unauthenticated',
    }),
  setLoading: () => set({ status: 'loading' }),
}));
