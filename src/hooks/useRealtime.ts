"use client";

import { useContext } from "react";
import {
  RealtimeContext,
  type RealtimeContextValue,
} from "@/components/realtime/realtime-provider";

export function useRealtime(): RealtimeContextValue {
  const ctx = useContext(RealtimeContext);
  if (!ctx) throw new Error("useRealtime must be used within <RealtimeProvider>");
  return ctx;
}
