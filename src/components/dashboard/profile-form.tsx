"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useToast } from "@/components/ui/toast";
import { getInitials } from "@/lib/utils";

interface ProfileData {
  firstName: string;
  lastName: string;
  username: string;
  phone: string;
  email: string;
  image: string;
}

export function ProfileForm({ initial }: { initial: ProfileData }) {
  const router = useRouter();
  const { toast } = useToast();
  const [form, setForm] = useState(initial);
  const [loading, setLoading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function onPhotoSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      toast({
        variant: "error",
        title: "Photo trop lourde",
        description: "Choisissez une image de moins de 4 Mo.",
      });
      return;
    }
    const reader = new FileReader();
    reader.onload = () =>
      setForm((f) => ({ ...f, image: String(reader.result) }));
    reader.readAsDataURL(file);
  }

  async function save() {
    setLoading(true);
    const res = await fetch("/api/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firstName: form.firstName,
        lastName: form.lastName,
        username: form.username,
        phone: form.phone,
        image: form.image,
      }),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Profil mis à jour" });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Échec", description: error });
    }
  }

  return (
    <Card className="max-w-2xl space-y-5 p-6">
      <div className="flex items-center gap-4">
        <Avatar className="size-16">
          {form.image && <AvatarImage src={form.image} alt="" />}
          <AvatarFallback className="text-lg">
            {getInitials(form.firstName, form.lastName)}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 space-y-1.5">
          <Label>Photo de profil</Label>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            capture="user"
            className="hidden"
            onChange={onPhotoSelected}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => fileInput.current?.click()}
            >
              <Camera className="size-4" />
              {form.image ? "Changer la photo" : "Ajouter une photo"}
            </Button>
            {form.image && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setForm({ ...form, image: "" })}
              >
                Retirer
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Prénom</Label>
          <Input
            value={form.firstName}
            onChange={(e) => setForm({ ...form, firstName: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Nom</Label>
          <Input
            value={form.lastName}
            onChange={(e) => setForm({ ...form, lastName: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Pseudo</Label>
          <Input
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Téléphone</Label>
          <Input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Email</Label>
          <Input value={form.email} disabled />
          <p className="text-xs text-muted-foreground">
            L&apos;email ne peut pas être modifié.
          </p>
        </div>
      </div>

      <Button onClick={save} disabled={loading}>
        {loading && <Loader2 className="size-4 animate-spin" />}
        Enregistrer les modifications
      </Button>
    </Card>
  );
}
