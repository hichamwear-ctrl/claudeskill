"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Gift, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { maxRedeemableEuro, REDEEM_STEP_EURO } from "@/lib/loyalty";

export function RedeemLoyalty({ points }: { points: number }) {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const max = maxRedeemableEuro(points);
  const [euro, setEuro] = useState(max >= REDEEM_STEP_EURO ? REDEEM_STEP_EURO : 0);

  async function redeem() {
    setLoading(true);
    const res = await fetch("/api/loyalty/redeem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ euro }),
    });
    const data = await res.json().catch(() => ({}));
    setLoading(false);
    if (res.ok) {
      setCode(data.data.code);
      toast({ variant: "success", title: `Bon de ${euro} € généré !` });
      router.refresh();
    } else {
      toast({ variant: "error", title: "Échange impossible", description: data.error });
    }
  }

  if (max < REDEEM_STEP_EURO) {
    return (
      <p className="text-sm text-muted-foreground">
        Cumulez au moins {100} points pour échanger votre premier bon de{" "}
        {REDEEM_STEP_EURO} €.
      </p>
    );
  }

  if (code) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-lg bg-gold/10 px-3 py-1.5 font-mono text-sm font-bold text-gold">
          {code}
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            navigator.clipboard?.writeText(code);
            setCopied(true);
          }}
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copied ? "Copié" : "Copier"}
        </Button>
        <span className="text-xs text-muted-foreground">
          Utilisez ce code à l&apos;étape paiement de votre prochaine réservation.
        </span>
      </div>
    );
  }

  const options: number[] = [];
  for (let e = REDEEM_STEP_EURO; e <= max; e += REDEEM_STEP_EURO) options.push(e);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={euro}
        onChange={(e) => setEuro(Number(e.target.value))}
        className="rounded-lg border border-border bg-secondary px-3 py-2 text-sm"
        aria-label="Montant du bon"
      >
        {options.map((e) => (
          <option key={e} value={e}>
            Bon de {e} €
          </option>
        ))}
      </select>
      <Button size="sm" onClick={redeem} disabled={loading}>
        {loading ? <Loader2 className="size-4 animate-spin" /> : <Gift className="size-4" />}
        Échanger
      </Button>
    </div>
  );
}
