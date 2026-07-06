"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Camera, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import type { BarberLevel } from "@prisma/client";

interface Photo {
  id: string;
  url: string;
  caption: string | null;
}

interface InitialProfile {
  bio: string;
  yearsExperience: number;
  level: BarberLevel;
  instagram: string;
  snapchat: string;
  photos: Photo[];
}

/** Barber-facing editor for the public profile fields + portfolio gallery. */
export function BarberProfileEditor({ initial }: { initial: InitialProfile }) {
  const router = useRouter();
  const { toast } = useToast();
  const [form, setForm] = useState({
    bio: initial.bio,
    yearsExperience: initial.yearsExperience,
    level: initial.level,
    instagram: initial.instagram,
    snapchat: initial.snapchat,
  });
  const [photos, setPhotos] = useState<Photo[]>(initial.photos);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function save() {
    setSaving(true);
    const res = await fetch("/api/barber/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSaving(false);
    if (res.ok) {
      toast({ variant: "success", title: "Profil mis à jour" });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Échec", description: error });
    }
  }

  function pickPhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      toast({ variant: "error", title: "Photo trop lourde (max 4 Mo)" });
      return;
    }
    const reader = new FileReader();
    reader.onload = async () => {
      setUploading(true);
      const res = await fetch("/api/barber/photos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: String(reader.result) }),
      });
      setUploading(false);
      if (res.ok) {
        const { data } = await res.json();
        setPhotos((p) => [data.photo, ...p]);
      } else {
        const { error } = await res.json().catch(() => ({ error: "Erreur" }));
        toast({ variant: "error", title: "Ajout impossible", description: error });
      }
    };
    reader.readAsDataURL(file);
  }

  async function removePhoto(id: string) {
    const res = await fetch(`/api/barber/photos/${id}`, { method: "DELETE" });
    if (res.ok) setPhotos((p) => p.filter((x) => x.id !== id));
  }

  return (
    <div className="space-y-6">
      <Card className="max-w-2xl space-y-5 p-6">
        <div className="space-y-1.5">
          <Label>Biographie</Label>
          <Textarea
            value={form.bio}
            onChange={(e) => setForm({ ...form, bio: e.target.value })}
            placeholder="Présentez votre parcours, vos spécialités…"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Années d&apos;expérience</Label>
            <Input
              type="number"
              min={0}
              value={form.yearsExperience}
              onChange={(e) =>
                setForm({ ...form, yearsExperience: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>Niveau</Label>
            <select
              className="flex h-11 w-full rounded-xl border border-input bg-secondary/50 px-4 text-sm focus-visible:border-gold/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/20"
              value={form.level}
              onChange={(e) =>
                setForm({ ...form, level: e.target.value as BarberLevel })
              }
            >
              <option value="JUNIOR">Junior</option>
              <option value="CONFIRME">Confirmé</option>
              <option value="EXPERT">Expert</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Instagram</Label>
            <Input
              value={form.instagram}
              onChange={(e) => setForm({ ...form, instagram: e.target.value })}
              placeholder="moncompte"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Snapchat</Label>
            <Input
              value={form.snapchat}
              onChange={(e) => setForm({ ...form, snapchat: e.target.value })}
              placeholder="moncompte"
            />
          </div>
        </div>
        <Button onClick={save} disabled={saving}>
          {saving && <Loader2 className="size-4 animate-spin" />}
          Enregistrer
        </Button>
      </Card>

      <Card className="max-w-2xl space-y-4 p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold">Galerie de réalisations</p>
            <p className="text-xs text-muted-foreground">
              Montrez vos plus belles coupes ({photos.length}/12).
            </p>
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={pickPhoto}
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fileInput.current?.click()}
            disabled={uploading || photos.length >= 12}
          >
            {uploading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Camera className="size-4" />
            )}
            Ajouter
          </Button>
        </div>
        {photos.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Aucune photo pour le moment.
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {photos.map((p) => (
              <div
                key={p.id}
                className="group relative aspect-square overflow-hidden rounded-xl bg-secondary"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.url} alt="" className="size-full object-cover" />
                <button
                  onClick={() => removePhoto(p.id)}
                  className="absolute right-1 top-1 rounded-lg bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
                  aria-label="Supprimer"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
