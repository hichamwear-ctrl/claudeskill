"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReservationStatus } from "@prisma/client";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

const CANCELLABLE: ReservationStatus[] = [
  "DEMANDE_ENVOYEE",
  "ACCEPTEE",
  "BARBER_ATTRIBUE",
];

export function CancelReservationButton({
  id,
  status,
}: {
  id: string;
  status: ReservationStatus;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  if (!CANCELLABLE.includes(status)) return null;

  async function cancel() {
    setLoading(true);
    const res = await fetch(`/api/reservations/${id}/cancel`, {
      method: "PATCH",
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Réservation annulée" });
      router.refresh();
    } else {
      toast({ variant: "error", title: "Annulation impossible" });
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={cancel} disabled={loading}>
      {loading ? <Loader2 className="size-4 animate-spin" /> : <X className="size-4" />}
      Annuler
    </Button>
  );
}
