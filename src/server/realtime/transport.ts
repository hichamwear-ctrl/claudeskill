/**
 * Server-side transport surface (PR #2, Phase 0).
 *
 * Re-exports the canonical `RealtimeTransport` interface (defined in the
 * client-safe `@/lib/realtime`) and provides an in-memory implementation used
 * as a dev/test fallback and by unit tests. The concrete Supabase transport
 * lives in `./supabase`.
 */
export type {
  RealtimeTransport,
  RealtimeEventMap,
  RealtimeEventName,
  RealtimeHandler,
  RealtimeSubscription,
  BarberPosition,
} from "@/lib/realtime";

import type {
  RealtimeTransport,
  RealtimeEventName,
  RealtimeHandler,
  RealtimeSubscription,
} from "@/lib/realtime";

type ChannelKey = string;

/**
 * Deterministic, dependency-free transport. Dispatches published events to
 * in-process subscribers. Safe default when Supabase is not configured, and
 * the substrate for transport unit tests.
 */
export class InMemoryTransport implements RealtimeTransport {
  private handlers = new Map<ChannelKey, Set<{ event: string; fn: RealtimeHandler<RealtimeEventName> }>>();

  async publish<E extends RealtimeEventName>(
    channel: string,
    event: E,
    payload: Parameters<RealtimeHandler<E>>[0],
  ): Promise<void> {
    const set = this.handlers.get(channel);
    if (!set) return;
    for (const entry of set) {
      if (entry.event === event) {
        (entry.fn as RealtimeHandler<E>)(payload);
      }
    }
  }

  subscribe<E extends RealtimeEventName>(
    channel: string,
    event: E,
    handler: RealtimeHandler<E>,
  ): RealtimeSubscription {
    const set = this.handlers.get(channel) ?? new Set();
    const entry = { event, fn: handler as RealtimeHandler<RealtimeEventName> };
    set.add(entry);
    this.handlers.set(channel, set);
    return {
      unsubscribe: () => {
        const current = this.handlers.get(channel);
        current?.delete(entry);
        if (current && current.size === 0) this.handlers.delete(channel);
      },
    };
  }

  unsubscribe(channel: string): void {
    this.handlers.delete(channel);
  }
}
