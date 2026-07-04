"use client";

import { useRouter } from "next/navigation";
import { Navigation, MapPin } from "lucide-react";
import type { GeoPoint } from "@/lib/realtime";
import { useReservationChannel } from "@/hooks/useReservationChannel";
import { SvgTrackingMap } from "@/components/map/svg-tracking-map";
import { formatDuration } from "@/lib/utils";

/**
 * Client-facing live tracking: shows the barber approaching on the map with a
 * live ETA. Falls back to the barber's last known position when no realtime
 * fix has arrived yet. Refreshes server data on status transitions.
 */
export function ClientTracking({
  reservationId,
  clientPoint,
  initialBarberPoint,
}: {
  reservationId: string;
  clientPoint: GeoPoint | null;
  initialBarberPoint: GeoPoint | null;
}) {
  const router = useRouter();
  const { position, eta } = useReservationChannel(reservationId, () =>
    router.refresh(),
  );
  const barber = position ?? initialBarberPoint;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 text-sm font-medium">
          <Navigation className="size-4 text-gold" />
          Votre barber est en route
        </p>
        {eta ? (
          <span className="rounded-full border border-gold/30 bg-gold/10 px-3 py-1 text-xs font-medium text-gold">
            Arrivée ~ {formatDuration(eta.minutes)} · {eta.distanceKm} km
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="size-3.5" /> Position en cours…
          </span>
        )}
      </div>
      <SvgTrackingMap client={clientPoint} barber={barber} className="aspect-[16/10]" />
    </div>
  );
}
