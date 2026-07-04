"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReservationStatus } from "@prisma/client";
import { STATUS_ORDER, STATUS_META } from "@/lib/status";
import { useToast } from "@/components/ui/toast";

const ALL: ReservationStatus[] = [...STATUS_ORDER, "ANNULEE"];

export function AdminStatusSelect({
  id,
  status,
}: {
  id: string;
  status: ReservationStatus;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [value, setValue] = useState<ReservationStatus>(status);
  const [loading, setLoading] = useState(false);

  async function change(next: ReservationStatus) {
    setValue(next);
    setLoading(true);
    const res = await fetch(`/api/reservations/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Statut mis à jour" });
      router.refresh();
    } else {
      setValue(status);
      toast({ variant: "error", title: "Échec de la mise à jour" });
    }
  }

  return (
    <select
      value={value}
      disabled={loading}
      onChange={(e) => change(e.target.value as ReservationStatus)}
      className="rounded-lg border border-border bg-secondary px-3 py-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/30"
    >
      {ALL.map((s) => (
        <option key={s} value={s}>
          {STATUS_META[s].label}
        </option>
      ))}
    </select>
  );
}
