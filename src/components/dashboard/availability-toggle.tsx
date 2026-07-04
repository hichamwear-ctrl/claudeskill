"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";

export function AvailabilityToggle({ initial }: { initial: boolean }) {
  const router = useRouter();
  const { toast } = useToast();
  const [available, setAvailable] = useState(initial);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !available;
    setAvailable(next);
    setLoading(true);
    const res = await fetch("/api/barber/availability", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isAvailable: next }),
    });
    setLoading(false);
    if (res.ok) {
      toast({
        variant: "success",
        title: next ? "Vous êtes disponible" : "Vous êtes indisponible",
      });
      router.refresh();
    } else {
      setAvailable(!next);
      toast({ variant: "error", title: "Erreur" });
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={cn(
        "flex items-center gap-3 rounded-full border px-4 py-2 text-sm font-medium transition-colors",
        available
          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-400"
          : "border-border bg-secondary text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "size-2.5 rounded-full",
          available ? "bg-emerald-400" : "bg-muted-foreground",
        )}
      />
      {available ? "Disponible" : "Indisponible"}
    </button>
  );
}
