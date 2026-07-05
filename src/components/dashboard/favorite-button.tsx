"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Heart } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

/**
 * Heart toggle to favorite/unfavorite a barber. Optimistic UI with rollback.
 */
export function FavoriteButton({
  barberId,
  initialFavorited,
  showLabel = false,
}: {
  barberId: string;
  initialFavorited: boolean;
  showLabel?: boolean;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [favorited, setFavorited] = useState(initialFavorited);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !favorited;
    setFavorited(next);
    setLoading(true);
    const res = next
      ? await fetch("/api/favorites", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ barberId }),
        })
      : await fetch(`/api/favorites/${barberId}`, { method: "DELETE" });
    setLoading(false);
    if (!res.ok) {
      setFavorited(!next);
      toast({ variant: "error", title: "Action impossible" });
      return;
    }
    router.refresh();
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      aria-pressed={favorited}
      aria-label={favorited ? "Retirer des favoris" : "Ajouter aux favoris"}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
        favorited
          ? "border-rose-400/30 bg-rose-400/10 text-rose-400"
          : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      <Heart className={cn("size-4", favorited && "fill-current")} />
      {showLabel && (favorited ? "Favori" : "Ajouter aux favoris")}
    </button>
  );
}
