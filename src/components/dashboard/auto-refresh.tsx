"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Lightweight real-time stand-in: revalidates server data on an interval.
 * Swap for Socket.io / Supabase Realtime subscriptions later without touching
 * the page components.
 */
export function AutoRefresh({ intervalMs = 15_000 }: { intervalMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);
  return null;
}
