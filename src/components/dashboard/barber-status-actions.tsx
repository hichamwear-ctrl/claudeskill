"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReservationStatus } from "@prisma/client";
import { Loader2, Check, X, Truck, MapPin, Scissors } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { BARBER_NEXT_STATUS, STATUS_META } from "@/lib/status";

const ICONS: Partial<Record<ReservationStatus, typeof Check>> = {
  ACCEPTEE: Check,
  EN_ROUTE: Truck,
  ARRIVE: MapPin,
  EN_COURS: Scissors,
  TERMINEE: Check,
  ANNULEE: X,
};

// Barber-facing labels (spec wording) that differ from the generic status name.
const LABELS: Partial<Record<ReservationStatus, string>> = {
  EN_ROUTE: "Je suis en route",
  ARRIVE: "Je suis arrivé",
  TERMINEE: "Terminer la prestation",
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

  async function call(url: string, body?: unknown, successTitle?: string) {
    setLoading(url);
    const res = await fetch(url, {
      method: body === undefined ? "POST" : "PATCH",
      headers: { "Content-Type": "application/json" },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    setLoading(null);
    if (res.ok) {
      if (successTitle) toast({ variant: "success", title: successTitle });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Action impossible", description: error });
    }
  }

  // Open request: accept (provisional) or decline — dedicated endpoints.
  if (status === "DEMANDE_ENVOYEE") {
    return (
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() => call(`/api/reservations/${id}/accept`, undefined, "Demande acceptée")}
          disabled={loading !== null}
        >
          {loading?.endsWith("/accept") ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Check className="size-4" />
          )}
          Accepter
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => call(`/api/reservations/${id}/decline`, undefined, "Demande refusée")}
          disabled={loading !== null}
        >
          {loading?.endsWith("/decline") ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <X className="size-4" />
          )}
          Refuser
        </Button>
      </div>
    );
  }

  // Barber accepted, waiting for the client's confirmation.
  if (status === "ACCEPTEE") {
    return (
      <p className="text-sm text-muted-foreground">
        En attente de la confirmation du client…
      </p>
    );
  }

  const next = BARBER_NEXT_STATUS[status] ?? [];
  if (next.length === 0) return null;

  async function updateStatus(target: ReservationStatus) {
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
            onClick={() => updateStatus(target)}
            disabled={loading !== null}
          >
            {loading === target ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Icon className="size-4" />
            )}
            {destructive ? "Annuler" : LABELS[target] ?? STATUS_META[target].label}
          </Button>
        );
      })}
    </div>
  );
}
