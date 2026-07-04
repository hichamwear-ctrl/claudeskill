"use client";

import { useEffect, useRef, useState } from "react";
import type { ReservationStatus } from "@prisma/client";
import type { BarberPosition } from "@/lib/realtime";
import { reservationChannel } from "@/lib/realtime";
import { useRealtime } from "@/hooks/useRealtime";

interface ChannelState {
  status: ReservationStatus | null;
  position: BarberPosition | null;
  eta: { minutes: number; distanceKm: number } | null;
}

/**
 * Subscribes to a reservation's realtime channel after obtaining a signed
 * authorization token from the server (a client cannot listen to a reservation
 * that isn't theirs). Returns the latest status/position/ETA, plus an
 * `onStatus` callback for side-effects (e.g. refreshing server data).
 */
export function useReservationChannel(
  reservationId: string | null,
  onStatus?: (status: ReservationStatus) => void,
): ChannelState {
  const rt = useRealtime();
  const [state, setState] = useState<ChannelState>({
    status: null,
    position: null,
    eta: null,
  });
  const onStatusRef = useRef(onStatus);
  onStatusRef.current = onStatus;

  useEffect(() => {
    if (!reservationId || rt.status === "disabled") return;
    let cancelled = false;
    const channel = reservationChannel(reservationId);
    const subs: Array<{ unsubscribe(): void }> = [];

    (async () => {
      // Authorize before subscribing; the server only issues a token for
      // reservations the current user may access.
      const res = await fetch(
        `/api/realtime/token?reservationId=${encodeURIComponent(reservationId)}`,
      );
      if (!res.ok || cancelled) return;

      subs.push(
        rt.subscribe(channel, "status", (p) => {
          setState((s) => ({ ...s, status: p.status }));
          onStatusRef.current?.(p.status);
        }),
      );
      subs.push(
        rt.subscribe(channel, "position", (p) =>
          setState((s) => ({ ...s, position: p.position })),
        ),
      );
      subs.push(
        rt.subscribe(channel, "eta", (p) =>
          setState((s) => ({ ...s, eta: { minutes: p.minutes, distanceKm: p.distanceKm } })),
        ),
      );
    })();

    return () => {
      cancelled = true;
      subs.forEach((s) => s.unsubscribe());
      rt.unsubscribe(channel);
    };
  }, [reservationId, rt]);

  return state;
}
