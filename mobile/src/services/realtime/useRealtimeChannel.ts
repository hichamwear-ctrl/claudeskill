import type { RealtimeChannel } from '@supabase/supabase-js';
import { useEffect } from 'react';

import { acquireChannel, releaseChannel } from './manager';

/**
 * Abonne un composant à un canal Realtime pour toute sa durée de vie.
 * `configure` doit être stable (mémoïsé) — inclure toute dépendance dans `deps`.
 * Les modules métier (chat, statut, GPS) s'appuient sur ce hook de base.
 */
export function useRealtimeChannel(
  topic: string | null,
  configure: (channel: RealtimeChannel) => void,
  deps: readonly unknown[] = [],
): void {
  useEffect(() => {
    if (!topic) return;
    acquireChannel(topic, configure);
    return () => releaseChannel(topic);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic, ...deps]);
}
