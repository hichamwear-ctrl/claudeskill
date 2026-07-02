import { useEffect, type ReactNode } from 'react';

import { setRealtimeAuth } from '@/services/realtime';
import { supabase } from '@/services/supabase/client';
import { useSessionStore } from '@/stores/sessionStore';

/**
 * Amorce la session au démarrage puis suit `onAuthStateChange` :
 * met à jour le `sessionStore` (userId + rôle) et propage le token à Realtime.
 */
export function SessionProvider({ children }: { children: ReactNode }): ReactNode {
  const setSession = useSessionStore((s) => s.setSession);

  useEffect(() => {
    let mounted = true;

    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return;
      setSession(session);
      setRealtimeAuth(session?.access_token ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setRealtimeAuth(session?.access_token ?? null);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [setSession]);

  return children;
}
