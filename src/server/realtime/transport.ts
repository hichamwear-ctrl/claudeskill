/**
 * Server transport surface + in-memory implementation (Phase 3).
 * Re-exports the canonical interface from the client-safe `@/lib/realtime`.
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

/** Deterministic, dependency-free transport — dev/test fallback. */
export class InMemoryTransport implements RealtimeTransport {
  private handlers = new Map<
    string,
    Set<{ event: string; fn: RealtimeHandler<RealtimeEventName> }>
  >();

  async publish<E extends RealtimeEventName>(
    channel: string,
    event: E,
    payload: Parameters<RealtimeHandler<E>>[0],
  ): Promise<void> {
    for (const entry of this.handlers.get(channel) ?? []) {
      if (entry.event === event) (entry.fn as RealtimeHandler<E>)(payload);
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
        const s = this.handlers.get(channel);
        s?.delete(entry);
        if (s && s.size === 0) this.handlers.delete(channel);
      },
    };
  }

  unsubscribe(channel: string): void {
    this.handlers.delete(channel);
  }
}
