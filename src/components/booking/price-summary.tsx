"use client";

import { useBookingStore } from "@/stores/booking";
import { computePrice } from "@/lib/pricing";
import { formatCurrency, formatDuration } from "@/lib/utils";
import { Separator } from "@/components/ui/misc";

export function usePriceBreakdown() {
  const persons = useBookingStore((s) => s.persons);
  const insideZone = useBookingStore((s) => s.insideZone);
  return computePrice(persons, { insideZone });
}

export function PriceSummary() {
  const breakdown = usePriceBreakdown();
  const insideZone = useBookingStore((s) => s.insideZone);

  return (
    <div className="glass sticky top-6 rounded-2xl p-6">
      <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Récapitulatif
      </p>

      <div className="mt-4 space-y-2 text-sm">
        <Line label="Sous-total" value={formatCurrency(breakdown.subtotal)} />
        <Line
          label={`Déplacement${insideZone ? " (Bruxelles)" : " (hors zone)"}`}
          value={
            breakdown.travelFee > 0
              ? formatCurrency(breakdown.travelFee)
              : "Offert"
          }
          muted={breakdown.travelFee === 0}
        />
        <Line
          label="Durée estimée"
          value={formatDuration(breakdown.durationMinutes)}
          muted
        />
      </div>

      <Separator className="my-4" />

      <div className="flex items-center justify-between">
        <span className="font-medium">Total</span>
        <span className="font-display text-2xl font-bold text-gold">
          {formatCurrency(breakdown.total)}
        </span>
      </div>
    </div>
  );
}

function Line({
  label,
  value,
  muted,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={muted ? "text-muted-foreground" : "font-medium"}>
        {value}
      </span>
    </div>
  );
}
