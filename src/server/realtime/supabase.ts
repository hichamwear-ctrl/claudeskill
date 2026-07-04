/**
 * Supabase-backed server transport (PR #2, Phase 0).
 *
 * `getServerTransport()` returns a Supabase Broadcast transport when the
 * service-role env is configured, otherwise a safe in-memory fallback so the
 * app builds and runs unchanged without Supabase credentials. Nothing here is
 * wired into the reservation flow yet — Phase 1 will call the publisher.
 */
import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type {
  RealtimeTransport,
  RealtimeEventName,
  RealtimeHandler,
  RealtimeSubscription,
} from "@/lib/realtime";
import { InMemoryTransport } from "./transport";

class SupabaseServerTransport implements RealtimeTransport {
  private client: SupabaseClient;

  constructor(url: string, serviceRoleKey: string) {
    this.client = createClient(url, serviceRoleKey, {
      auth: { persistSession: false },
      realtime: { params: { eventsPerSecond: 10 } },
    });
  }

  async publish<E extends RealtimeEventName>(
    channel: string,
    event: E,
    payload: Parameters<RealtimeHandler<E>>[0],
  ): Promise<void> {
    const ch = this.client.channel(channel, { config: { broadcast: { ack: true } } });
    await new Promise<void>((resolve) => {
      ch.subscribe((status) => {
        if (status === "SUBSCRIBED") resolve();
      });
      // Fail-open: never block the request path on realtime delivery.
      setTimeout(resolve, 1500);
    });
    await ch.send({ type: "broadcast", event, payload });
    await this.client.removeChannel(ch);
  }

  // The server side only publishes; subscription is a client concern.
  subscribe(): RealtimeSubscription {
    throw new Error("Server transport does not subscribe; use the client provider.");
  }

  unsubscribe(): void {
    /* no-op on the server */
  }
}

let cached: RealtimeTransport | null = null;

export function getServerTransport(): RealtimeTransport {
  if (cached) return cached;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  cached =
    url && serviceRoleKey
      ? new SupabaseServerTransport(url, serviceRoleKey)
      : new InMemoryTransport();

  return cached;
}
