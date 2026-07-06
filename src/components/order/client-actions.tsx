"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

/**
 * Client validates or rejects the barber who accepted their request.
 * On confirm the order becomes definitive (chat + calls open); on refuse the
 * request is re-opened to other barbers.
 */
export function ConfirmBarberButtons({ reservationId }: { reservationId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [pending, setPending] = useState<null | "CONFIRM" | "REFUSE">(null);

  async function decide(decision: "CONFIRM" | "REFUSE") {
    setPending(decision);
    const res = await fetch(`/api/reservations/${reservationId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    setPending(null);
    if (res.ok) {
      toast({
        variant: "success",
        title: decision === "CONFIRM" ? "Barber confirmé" : "Demande relancée",
      });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Action impossible", description: error });
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Button onClick={() => decide("CONFIRM")} disabled={pending !== null}>
        {pending === "CONFIRM" ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Check className="size-4" />
        )}
        Confirmer ce barber
      </Button>
      <Button
        variant="outline"
        onClick={() => decide("REFUSE")}
        disabled={pending !== null}
      >
        {pending === "REFUSE" ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <X className="size-4" />
        )}
        Choisir un autre barber
      </Button>
    </div>
  );
}
