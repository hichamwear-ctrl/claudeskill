"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Loader2, CalendarOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import {
  UNAVAILABILITY_LABELS,
  isValidUnavailability,
  type UnavailabilityType,
} from "@/lib/unavailability";
import { formatDate } from "@/lib/utils";

interface Item {
  id: string;
  date: string | Date;
  allDay: boolean;
  startTime: string | null;
  endTime: string | null;
  type: UnavailabilityType;
  reason: string | null;
}

const TYPE_STYLE: Record<UnavailabilityType, string> = {
  BREAK: "border-amber-400/30 bg-amber-400/10 text-amber-400",
  LEAVE: "border-sky-400/30 bg-sky-400/10 text-sky-400",
  OFF: "border-rose-400/30 bg-rose-400/10 text-rose-400",
};

const EMPTY = {
  date: "",
  allDay: true,
  startTime: "12:00",
  endTime: "13:00",
  type: "OFF" as UnavailabilityType,
  reason: "",
};

export function UnavailabilityManager({ initial }: { initial: Item[] }) {
  const router = useRouter();
  const { toast } = useToast();
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(false);

  async function add() {
    if (!form.date) {
      toast({ variant: "error", title: "Choisissez une date" });
      return;
    }
    if (!isValidUnavailability(form)) {
      toast({ variant: "error", title: "Plage horaire invalide" });
      return;
    }
    setLoading(true);
    const res = await fetch("/api/barber/unavailability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: form.date,
        allDay: form.allDay,
        startTime: form.allDay ? undefined : form.startTime,
        endTime: form.allDay ? undefined : form.endTime,
        type: form.type,
        reason: form.reason || undefined,
      }),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Indisponibilité ajoutée" });
      setForm(EMPTY);
      router.refresh();
    } else {
      toast({ variant: "error", title: "Ajout impossible" });
    }
  }

  async function remove(id: string) {
    const res = await fetch(`/api/barber/unavailability/${id}`, { method: "DELETE" });
    if (res.ok) {
      toast({ variant: "success", title: "Supprimée" });
      router.refresh();
    }
  }

  return (
    <Card className="max-w-2xl space-y-5 p-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Date</Label>
          <Input
            type="date"
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Type</Label>
          <select
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value as UnavailabilityType })}
            className="h-11 w-full rounded-xl border border-input bg-secondary/50 px-4 text-sm"
          >
            {(Object.keys(UNAVAILABILITY_LABELS) as UnavailabilityType[]).map((t) => (
              <option key={t} value={t}>
                {UNAVAILABILITY_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.allDay}
          onChange={(e) => setForm({ ...form, allDay: e.target.checked })}
          className="size-4 accent-[#D4AF37]"
        />
        Toute la journée
      </label>

      {!form.allDay && (
        <div className="flex items-center gap-3">
          <Input
            type="time"
            value={form.startTime}
            onChange={(e) => setForm({ ...form, startTime: e.target.value })}
            className="w-32"
            aria-label="Début"
          />
          <span className="text-muted-foreground">→</span>
          <Input
            type="time"
            value={form.endTime}
            onChange={(e) => setForm({ ...form, endTime: e.target.value })}
            className="w-32"
            aria-label="Fin"
          />
        </div>
      )}

      <div className="space-y-1.5">
        <Label>Motif (optionnel)</Label>
        <Input
          value={form.reason}
          onChange={(e) => setForm({ ...form, reason: e.target.value })}
          placeholder="Congé, rendez-vous…"
        />
      </div>

      <Button onClick={add} disabled={loading}>
        {loading ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
        Ajouter
      </Button>

      <div className="space-y-2 border-t border-border pt-4">
        {initial.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <CalendarOff className="size-4" /> Aucune indisponibilité à venir.
          </p>
        ) : (
          initial.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between rounded-xl border border-border bg-secondary/30 px-4 py-2.5"
            >
              <div className="flex items-center gap-3">
                <Badge className={TYPE_STYLE[u.type]}>{UNAVAILABILITY_LABELS[u.type]}</Badge>
                <div className="text-sm">
                  <span className="font-medium">{formatDate(u.date)}</span>
                  <span className="text-muted-foreground">
                    {u.allDay ? " · journée" : ` · ${u.startTime}–${u.endTime}`}
                    {u.reason ? ` · ${u.reason}` : ""}
                  </span>
                </div>
              </div>
              <button
                onClick={() => remove(u.id)}
                className="text-muted-foreground transition-colors hover:text-rose-400"
                aria-label="Supprimer"
              >
                <Trash2 className="size-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
