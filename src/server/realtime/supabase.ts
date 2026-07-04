/**
 * Supabase Broadcast server transport (Phase 3), with in-memory fallback when
 * the service-role env is missing so the app runs unchanged without Supabase.
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
  constructor(url: string, key: string) {
    this.client = createClient(url, key, { auth: { persistSession: false } });
  }
  async publish<E extends RealtimeEventName>(
    channel: string,
    event: E,
    payload: Parameters<RealtimeHandler<E>>[0],
  ): Promise<void> {
    const ch = this.client.channel(channel);
    await new Promise<void>((resolve) => {
      ch.subscribe((s) => s === "SUBSCRIBED" && resolve());
      setTimeout(resolve, 1500); // fail-open, never block the request path
    });
    await ch.send({ type: "broadcast", event, payload });
    await this.client.removeChannel(ch);
  }
  subscribe(): RealtimeSubscription {
    throw new Error("Server transport does not subscribe.");
  }
  unsubscribe(): void {}
}

let cached: RealtimeTransport | null = null;
export function getServerTransport(): RealtimeTransport {
  if (cached) return cached;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  cached =
    url && key ? new SupabaseServerTransport(url, key) : new InMemoryTransport();
  return cached;
}
