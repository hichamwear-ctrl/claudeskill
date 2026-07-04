"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CreditCard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

export function PayButton({ reservationId }: { reservationId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  async function pay() {
    setLoading(true);
    const res = await fetch("/api/payments/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reservationId }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setLoading(false);
      toast({ variant: "error", title: "Paiement impossible", description: data.error });
      return;
    }
    if (data.data?.url) {
      window.location.href = data.data.url; // hosted checkout (Stripe)
      return;
    }
    setLoading(false);
    toast({ variant: "success", title: "Paiement confirmé", description: "Facture disponible." });
    router.refresh();
  }

  return (
    <Button size="sm" onClick={pay} disabled={loading}>
      {loading ? <Loader2 className="size-4 animate-spin" /> : <CreditCard className="size-4" />}
      Payer en ligne
    </Button>
  );
}
