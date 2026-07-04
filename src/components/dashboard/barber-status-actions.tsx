"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReservationStatus } from "@prisma/client";
import { Loader2, Check, X, Truck, MapPin, Scissors, Flag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { BARBER_NEXT_STATUS, STATUS_META } from "@/lib/status";

const ICONS: Partial<Record<ReservationStatus, typeof Check>> = {
  ACCEPTEE: Check,
  BARBER_ATTRIBUE: Flag,
  EN_ROUTE: Truck,
  ARRIVE: MapPin,
  EN_COURS: Scissors,
  TERMINEE: Check,
  ANNULEE: X,
};

export function BarberStatusActions({
  id,
  status,
}: {
  id: string;
  status: ReservationStatus;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState<string | null>(null);

  const next = BARBER_NEXT_STATUS[status] ?? [];
  if (next.length === 0) return null;

  async function update(target: ReservationStatus) {
    setLoading(target);
    const res = await fetch(`/api/reservations/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: target }),
    });
    setLoading(null);
    if (res.ok) {
      toast({ variant: "success", title: `Statut : ${STATUS_META[target].label}` });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Action impossible", description: error });
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {next.map((target) => {
        const Icon = ICONS[target] ?? Check;
        const destructive = target === "ANNULEE";
        return (
          <Button
            key={target}
            size="sm"
            variant={destructive ? "ghost" : "default"}
            onClick={() => update(target)}
            disabled={loading !== null}
          >
            {loading === target ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Icon className="size-4" />
            )}
            {destructive ? "Refuser" : STATUS_META[target].label}
          </Button>
        );
      })}
    </div>
  );
}
