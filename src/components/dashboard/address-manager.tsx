"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Address } from "@prisma/client";
import { MapPin, Plus, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";

const EMPTY = { label: "Domicile", street: "", number: "", postalCode: "", city: "Bruxelles" };

export function AddressManager({ addresses }: { addresses: Address[] }) {
  const router = useRouter();
  const { toast } = useToast();
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(addresses.length === 0);
  const [loading, setLoading] = useState(false);

  async function addAddress() {
    if (!form.street || !form.postalCode || !form.city) {
      toast({ variant: "error", title: "Champs requis manquants" });
      return;
    }
    setLoading(true);
    const res = await fetch("/api/addresses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Adresse ajoutée" });
      setForm(EMPTY);
      setShowForm(false);
      router.refresh();
    } else {
      toast({ variant: "error", title: "Erreur lors de l'ajout" });
    }
  }

  async function remove(id: string) {
    const res = await fetch(`/api/addresses/${id}`, { method: "DELETE" });
    if (res.ok) {
      toast({ variant: "success", title: "Adresse supprimée" });
      router.refresh();
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2">
        {addresses.map((a) => (
          <Card key={a.id} className="flex items-start justify-between p-4">
            <div className="flex items-start gap-3">
              <span className="flex size-9 items-center justify-center rounded-lg bg-secondary text-gold">
                <MapPin className="size-4" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">{a.label}</p>
                  {a.isDefault && (
                    <Badge className="border-gold/30 bg-gold/10 text-gold">
                      Par défaut
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {a.street} {a.number}, {a.postalCode} {a.city}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {a.insideZone ? "✓ Dans la zone Bruxelles" : "⚠ Hors zone"}
                </p>
              </div>
            </div>
            <button
              onClick={() => remove(a.id)}
              className="text-muted-foreground transition-colors hover:text-rose-400"
            >
              <Trash2 className="size-4" />
            </button>
          </Card>
        ))}
      </div>

      {showForm ? (
        <Card className="space-y-4 p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5 sm:col-span-1">
              <Label>Libellé</Label>
              <Input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Rue</Label>
              <Input
                value={form.street}
                onChange={(e) => setForm({ ...form, street: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Numéro</Label>
              <Input
                value={form.number}
                onChange={(e) => setForm({ ...form, number: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Code postal</Label>
              <Input
                value={form.postalCode}
                onChange={(e) => setForm({ ...form, postalCode: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Ville</Label>
              <Input
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={addAddress} disabled={loading}>
              {loading && <Loader2 className="size-4 animate-spin" />}
              Enregistrer
            </Button>
            {addresses.length > 0 && (
              <Button variant="ghost" onClick={() => setShowForm(false)}>
                Annuler
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <Button variant="secondary" onClick={() => setShowForm(true)}>
          <Plus className="size-4" />
          Ajouter une adresse
        </Button>
      )}
    </div>
  );
}
