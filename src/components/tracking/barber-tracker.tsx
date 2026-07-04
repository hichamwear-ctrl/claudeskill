"use client";

import { Navigation, MapPinOff, Loader2 } from "lucide-react";
import { useBarberGeolocation } from "@/hooks/useBarberGeolocation";
import { cn } from "@/lib/utils";

/**
 * Barber-side control: streams the barber's position to the client while the
 * mission is EN_ROUTE/ARRIVE. Auto-stops when `active` is false.
 */
export function BarberTracker({
  reservationId,
  active,
}: {
  reservationId: string;
  active: boolean;
}) {
  const state = useBarberGeolocation(reservationId, active);

  const label =
    state === "tracking"
      ? "Partage de position actif"
      : state === "denied"
        ? "Localisation refusée"
        : state === "unsupported"
          ? "Géolocalisation indisponible"
          : "Activation du partage…";

  const tone =
    state === "tracking"
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-400"
      : state === "denied" || state === "unsupported"
        ? "border-rose-400/30 bg-rose-400/10 text-rose-400"
        : "border-border bg-secondary text-muted-foreground";

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium",
        tone,
      )}
    >
      {state === "tracking" ? (
        <Navigation className="size-3.5" />
      ) : state === "denied" || state === "unsupported" ? (
        <MapPinOff className="size-3.5" />
      ) : (
        <Loader2 className="size-3.5 animate-spin" />
      )}
      {label}
    </div>
  );
}
