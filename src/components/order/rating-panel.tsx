"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Star, Loader2, Camera, TriangleAlert, LifeBuoy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

/**
 * End-of-order page shown to the client once the barber has arrived: rate the
 * barber (1–5), optional comment + photo, plus "signaler un problème" and
 * "besoin d'aide" shortcuts.
 */
export function RatingPanel({ reservationId }: { reservationId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [photo, setPhoto] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"rate" | "PROBLEM" | "HELP">("rate");
  const [reportMsg, setReportMsg] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  function onPhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      toast({ variant: "error", title: "Photo trop lourde (max 4 Mo)" });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setPhoto(String(reader.result));
    reader.readAsDataURL(file);
  }

  async function submitReview() {
    if (rating === 0) {
      toast({ variant: "error", title: "Sélectionnez une note" });
      return;
    }
    setLoading(true);
    const res = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reservationId,
        rating,
        comment: comment || undefined,
        photo: photo || undefined,
      }),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Merci pour votre avis !" });
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Enregistrement impossible", description: error });
    }
  }

  async function submitReport(type: "PROBLEM" | "HELP") {
    if (!reportMsg.trim()) {
      toast({ variant: "error", title: "Décrivez votre demande" });
      return;
    }
    setLoading(true);
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reservationId, type, message: reportMsg }),
    });
    setLoading(false);
    if (res.ok) {
      toast({
        variant: "success",
        title: type === "PROBLEM" ? "Problème signalé" : "Demande envoyée",
        description: "Notre équipe vous recontacte au plus vite.",
      });
      setReportMsg("");
      setMode("rate");
    } else {
      toast({ variant: "error", title: "Envoi impossible" });
    }
  }

  if (mode !== "rate") {
    const isProblem = mode === "PROBLEM";
    return (
      <div className="space-y-3">
        <p className="text-sm font-medium">
          {isProblem ? "Signaler un problème" : "Besoin d'aide"}
        </p>
        <Textarea
          value={reportMsg}
          onChange={(e) => setReportMsg(e.target.value)}
          placeholder={
            isProblem
              ? "Décrivez ce qui s'est mal passé…"
              : "Expliquez-nous comment vous aider…"
          }
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={() => submitReport(mode)} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Envoyer
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setMode("rate")}>
            Annuler
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <p className="text-sm font-medium">Notez votre barber</p>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onMouseEnter={() => setHover(n)}
              onMouseLeave={() => setHover(0)}
              onClick={() => setRating(n)}
            >
              <Star
                className={cn(
                  "size-7 transition-colors",
                  (hover || rating) >= n
                    ? "fill-gold text-gold"
                    : "text-muted-foreground",
                )}
              />
            </button>
          ))}
        </div>
        <Textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Un commentaire (optionnel)…"
        />
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={onPhoto}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => fileInput.current?.click()}
          >
            <Camera className="size-4" />
            {photo ? "Changer la photo" : "Ajouter une photo"}
          </Button>
          {photo && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photo} alt="" className="size-10 rounded-lg object-cover" />
          )}
        </div>
        <Button size="sm" onClick={submitReview} disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" />}
          Envoyer mon avis
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-border pt-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setMode("PROBLEM")}
        >
          <TriangleAlert className="size-4" />
          Signaler un problème
        </Button>
        <Button variant="outline" size="sm" onClick={() => setMode("HELP")}>
          <LifeBuoy className="size-4" />
          Besoin d&apos;aide
        </Button>
      </div>
    </div>
  );
}
