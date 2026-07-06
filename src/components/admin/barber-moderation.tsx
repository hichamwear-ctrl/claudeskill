"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

type Action =
  | "APPROVE"
  | "REFUSE"
  | "BAN"
  | "UNBAN"
  | "SUSPEND"
  | "UNSUSPEND"
  | "DELETE";

const LABELS: Record<Action, string> = {
  APPROVE: "Valider",
  REFUSE: "Refuser",
  BAN: "Bannir",
  UNBAN: "Débannir",
  SUSPEND: "Suspendre",
  UNSUSPEND: "Réactiver",
  DELETE: "Supprimer",
};

export function BarberModeration({
  barberId,
  actions,
}: {
  barberId: string;
  actions: Action[];
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [pending, setPending] = useState<Action | null>(null);

  async function run(action: Action) {
    if (action === "DELETE" && !confirm("Supprimer définitivement ce compte ?"))
      return;
    setPending(action);
    const res = await fetch("/api/admin/barbers", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ barberId, action }),
    });
    setPending(null);
    if (res.ok) {
      toast({ variant: "success", title: `${LABELS[action]} — effectué` });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Action impossible", description: error });
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const danger = action === "DELETE" || action === "BAN" || action === "REFUSE";
        return (
          <Button
            key={action}
            size="sm"
            variant={
              action === "APPROVE"
                ? "default"
                : danger
                  ? "destructive"
                  : "secondary"
            }
            onClick={() => run(action)}
            disabled={pending !== null}
          >
            {pending === action && <Loader2 className="size-4 animate-spin" />}
            {LABELS[action]}
          </Button>
        );
      })}
    </div>
  );
}
