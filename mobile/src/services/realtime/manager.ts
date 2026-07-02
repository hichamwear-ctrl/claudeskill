import type { RealtimeChannel } from '@supabase/supabase-js';

import { supabase } from '@/services/supabase/client';

/**
 * Gestionnaire de canaux Realtime.
 *
 * - Canaux **privés** (`config.private = true`) : l'accès est autorisé côté base
 *   (`can_access_topic` / `can_publish_topic`).
 * - **Réutilisation par topic** avec comptage de références : plusieurs
 *   abonnés d'écran partagent un seul canal ; il est retiré au dernier départ.
 */
interface Entry {
  channel: RealtimeChannel;
  refs: number;
}

const registry = new Map<string, Entry>();

/**
 * Acquiert (ou crée) un canal pour `topic`. `configure` branche les listeners
 * AVANT l'abonnement (obligatoire pour Postgres Changes/Broadcast).
 */
export function acquireChannel(topic: string, configure: (channel: RealtimeChannel) => void): RealtimeChannel {
  const existing = registry.get(topic);
  if (existing) {
    existing.refs += 1;
    return existing.channel;
  }
  const channel = supabase.channel(topic, { config: { private: true } });
  configure(channel);
  channel.subscribe();
  registry.set(topic, { channel, refs: 1 });
  return channel;
}

/** Libère une référence ; retire le canal quand plus personne ne l'écoute. */
export function releaseChannel(topic: string): void {
  const entry = registry.get(topic);
  if (!entry) return;
  entry.refs -= 1;
  if (entry.refs <= 0) {
    void supabase.removeChannel(entry.channel);
    registry.delete(topic);
  }
}

/**
 * Propage le JWT courant à Realtime (à appeler à chaque changement de session).
 * Sans token valide, les canaux privés sont refusés.
 */
export function setRealtimeAuth(accessToken: string | null): void {
  supabase.realtime.setAuth(accessToken ?? '');
}
