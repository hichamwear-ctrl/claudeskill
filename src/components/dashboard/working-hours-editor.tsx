"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import {
  WEEKDAYS,
  isValidRange,
  mergeWeek,
  type WorkingHourDraft,
} from "@/lib/working-hours";
import { cn } from "@/lib/utils";

export function WorkingHoursEditor({
  initial,
}: {
  initial: Array<{ weekday: number; startTime: string; endTime: string; enabled: boolean }>;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [week, setWeek] = useState<WorkingHourDraft[]>(() => mergeWeek(initial));
  const [saving, setSaving] = useState(false);

  function update(weekday: number, patch: Partial<WorkingHourDraft>) {
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, ...patch } : d)));
  }

  async function save() {
    const invalid = week.find((d) => d.enabled && !isValidRange(d.startTime, d.endTime));
    if (invalid) {
      toast({
        variant: "error",
        title: "Plage horaire invalide",
        description: `${WEEKDAYS[invalid.weekday]} : l'heure de fin doit suivre le début.`,
      });
      return;
    }
    setSaving(true);
    const res = await fetch("/api/barber/working-hours", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hours: week }),
    });
    setSaving(false);
    if (res.ok) {
      toast({ variant: "success", title: "Disponibilités enregistrées" });
      router.refresh();
    } else {
      toast({ variant: "error", title: "Échec de l'enregistrement" });
    }
  }

  return (
    <Card className="max-w-2xl p-6">
      <div className="space-y-3">
        {week.map((d) => (
          <div
            key={d.weekday}
            className={cn(
              "flex flex-wrap items-center gap-3 rounded-xl border p-3 transition-colors",
              d.enabled ? "border-border bg-secondary/30" : "border-border/50 opacity-60",
            )}
          >
            <label className="flex w-32 items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                checked={d.enabled}
                onChange={(e) => update(d.weekday, { enabled: e.target.checked })}
                className="size-4 accent-[#D4AF37]"
                aria-label={`Activer ${WEEKDAYS[d.weekday]}`}
              />
              {WEEKDAYS[d.weekday]}
            </label>
            <Input
              type="time"
              value={d.startTime}
              disabled={!d.enabled}
              onChange={(e) => update(d.weekday, { startTime: e.target.value })}
              className="w-32"
              aria-label={`Début ${WEEKDAYS[d.weekday]}`}
            />
            <span className="text-muted-foreground">→</span>
            <Input
              type="time"
              value={d.endTime}
              disabled={!d.enabled}
              onChange={(e) => update(d.weekday, { endTime: e.target.value })}
              className="w-32"
              aria-label={`Fin ${WEEKDAYS[d.weekday]}`}
            />
          </div>
        ))}
      </div>
      <Button onClick={save} disabled={saving} className="mt-5">
        {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
        Enregistrer
      </Button>
    </Card>
  );
}
