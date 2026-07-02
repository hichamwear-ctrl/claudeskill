import { useEffect, useState } from 'react';

import { channels } from '@/constants/channels';
import { acquireChannel, releaseChannel } from '@/services/realtime';

/**
 * Disponibilité de l'intervenant via Realtime Presence (`operator:presence`).
 * `online` → `track()` ; retour hors-ligne / démontage → `untrack()`.
 */
export function useAvailability() {
  const [online, setOnline] = useState(false);

  useEffect(() => {
    if (!online) return;
    const topic = channels.operatorPresence();
    const channel = acquireChannel(topic, () => {});
    void channel.track({ online: true, at: Date.now() });
    return () => {
      void channel.untrack();
      releaseChannel(topic);
    };
  }, [online]);

  return { online, setOnline };
}
