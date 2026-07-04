"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Star, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

export function ReviewForm({ reservationId }: { reservationId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (rating === 0) {
      toast({ variant: "error", title: "Sélectionnez une note" });
      return;
    }
    setLoading(true);
    const res = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reservationId, rating, comment: comment || undefined }),
    });
    setLoading(false);
    if (res.ok) {
      toast({ variant: "success", title: "Merci pour votre avis !" });
      router.refresh();
    } else {
      toast({ variant: "error", title: "Impossible d'enregistrer l'avis" });
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">Notez votre prestation</p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(0)}
            onClick={() => setRating(n)}
          >
            <Star
              className={cn(
                "size-6 transition-colors",
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
      <Button size="sm" onClick={submit} disabled={loading}>
        {loading && <Loader2 className="size-4 animate-spin" />}
        Envoyer mon avis
      </Button>
    </div>
  );
}
