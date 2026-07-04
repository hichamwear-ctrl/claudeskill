"use client";

import { useEffect, useRef, useState } from "react";

export type GeoTrackingState = "idle" | "tracking" | "denied" | "unsupported";

interface Options {
  /** Minimum ms between server posts (battery / bandwidth friendly). */
  throttleMs?: number;
  /** High accuracy drains battery — off by default. */
  highAccuracy?: boolean;
}

/**
 * Streams the barber's position to the tracking API while `active` is true.
 *
 * - Throttles server posts (default 5s) to spare battery/data.
 * - Auto-stops (clears the geolocation watch) when `active` becomes false —
 *   i.e. when the mission is no longer EN_ROUTE/ARRIVE.
 * - Retries automatically after a transient position error.
 */
export function useBarberGeolocation(
  reservationId: string,
  active: boolean,
  { throttleMs = 5000, highAccuracy = false }: Options = {},
): GeoTrackingState {
  const [state, setState] = useState<GeoTrackingState>("idle");
  const lastSent = useRef(0);
  const retry = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!active) {
      setState("idle");
      return;
    }
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setState("unsupported");
      return;
    }

    let watchId: number | null = null;
    let cancelled = false;

    const post = async (lat: number, lng: number) => {
      const now = Date.now();
      if (now - lastSent.current < throttleMs) return;
      lastSent.current = now;
      await fetch("/api/tracking", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reservationId, lat, lng }),
      }).catch(() => null);
    };

    const start = () => {
      watchId = navigator.geolocation.watchPosition(
        (pos) => {
          if (cancelled) return;
          setState("tracking");
          void post(pos.coords.latitude, pos.coords.longitude);
        },
        (err) => {
          if (cancelled) return;
          if (err.code === err.PERMISSION_DENIED) {
            setState("denied");
            return;
          }
          // Transient error — restart the watch shortly (reconnection).
          if (watchId !== null) navigator.geolocation.clearWatch(watchId);
          retry.current = setTimeout(start, 4000);
        },
        { enableHighAccuracy: highAccuracy, maximumAge: 4000, timeout: 15000 },
      );
    };

    start();

    return () => {
      cancelled = true;
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
      if (retry.current) clearTimeout(retry.current);
    };
  }, [reservationId, active, throttleMs, highAccuracy]);

  return state;
}
