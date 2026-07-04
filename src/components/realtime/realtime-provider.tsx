"use client";

/**
 * RealtimeProvider (Phase 3) — owns the browser realtime connection and exposes
 * a typed subscribe/unsubscribe context. Inert (status "disabled") without
 * Supabase env, so the app behaves exactly as before when unconfigured.
 * Reconnection is handled by supabase-js; channels are torn down on unmount.
 */
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  createClient,
  type SupabaseClient,
  type RealtimeChannel,
} from "@supabase/supabase-js";
import type {
  RealtimeEventName,
  RealtimeHandler,
  RealtimeSubscription,
} from "@/lib/realtime";

export type RealtimeStatus = "disabled" | "connecting" | "connected" | "error";

export interface RealtimeContextValue {
  status: RealtimeStatus;
  subscribe<E extends RealtimeEventName>(
    channel: string,
    event: E,
    handler: RealtimeHandler<E>,
  ): RealtimeSubscription;
  unsubscribe(channel: string): void;
}

const NOOP: RealtimeSubscription = { unsubscribe() {} };
export const RealtimeContext = createContext<RealtimeContextValue | null>(null);

function readConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return url && anonKey ? { url, anonKey } : null;
}

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const config = useMemo(readConfig, []);
  const [status, setStatus] = useState<RealtimeStatus>(
    config ? "connecting" : "disabled",
  );
  const clientRef = useRef<SupabaseClient | null>(null);
  const channelsRef = useRef<Map<string, RealtimeChannel>>(new Map());

  useEffect(() => {
    if (!config) return;
    const client = createClient(config.url, config.anonKey, {
      auth: { persistSession: false },
      realtime: { params: { eventsPerSecond: 10 } },
    });
    clientRef.current = client;
    setStatus("connected");
    const channels = channelsRef.current;
    return () => {
      for (const ch of channels.values()) client.removeChannel(ch);
      channels.clear();
      clientRef.current = null;
    };
  }, [config]);

  const subscribe = useCallback(
    <E extends RealtimeEventName>(
      channel: string,
      event: E,
      handler: RealtimeHandler<E>,
    ): RealtimeSubscription => {
      const client = clientRef.current;
      if (!client) return NOOP;
      const existing = channelsRef.current.get(channel);
      const ch = existing ?? client.channel(channel);
      ch.on("broadcast", { event }, (message) => {
        const { payload } = message as unknown as {
          payload: Parameters<RealtimeHandler<E>>[0];
        };
        handler(payload);
      });
      if (!existing) {
        ch.subscribe((s) => {
          if (s === "CHANNEL_ERROR" || s === "TIMED_OUT") setStatus("error");
        });
        channelsRef.current.set(channel, ch);
      }
      return {
        unsubscribe: () => {
          const cur = channelsRef.current.get(channel);
          if (cur) {
            client.removeChannel(cur);
            channelsRef.current.delete(channel);
          }
        },
      };
    },
    [],
  );

  const unsubscribe = useCallback((channel: string) => {
    const client = clientRef.current;
    const ch = channelsRef.current.get(channel);
    if (client && ch) {
      client.removeChannel(ch);
      channelsRef.current.delete(channel);
    }
  }, []);

  const value = useMemo<RealtimeContextValue>(
    () => ({ status, subscribe, unsubscribe }),
    [status, subscribe, unsubscribe],
  );

  return (
    <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>
  );
}
