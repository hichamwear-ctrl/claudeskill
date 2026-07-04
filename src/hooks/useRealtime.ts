"use client";

/**
 * useRealtime (PR #2, Phase 0).
 *
 * Access point to the realtime context. Feature hooks in later phases
 * (e.g. `useReservationChannel`) will build on top of this — no component ever
 * touches the Supabase SDK directly.
 */
import { useContext } from "react";
import {
  RealtimeContext,
  type RealtimeContextValue,
} from "@/components/realtime/realtime-provider";

export function useRealtime(): RealtimeContextValue {
  const ctx = useContext(RealtimeContext);
  if (!ctx) {
    throw new Error("useRealtime must be used within a <RealtimeProvider>");
  }
  return ctx;
}
