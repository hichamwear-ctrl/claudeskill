import type { Metadata } from "next";
import { Sparkles, TrendingUp } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, StatCard } from "@/components/dashboard/common";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/misc";
import { RedeemLoyalty } from "@/components/dashboard/redeem-loyalty";
import { TIERS, tierFor } from "@/lib/loyalty";
import { formatDateTime, cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Fidélité" };
export const dynamic = "force-dynamic";

export default async function LoyaltyPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const [user, txns] = await Promise.all([
    prisma.user.findUnique({
      where: { id: session.user.id },
      select: { loyaltyPoints: true },
    }),
    prisma.loyaltyTransaction.findMany({
      where: { userId: session.user.id },
      orderBy: { createdAt: "desc" },
      take: 20,
    }),
  ]);

  const points = user?.loyaltyPoints ?? 0;
  const { current, next, toNext } = tierFor(points);
  const progress = next ? ((points - current.min) / (next.min - current.min)) * 100 : 100;

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Programme de fidélité"
        subtitle="Gagnez des points à chaque prestation, échangez-les en bons."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Mes points" value={points} icon={Sparkles} accent />
        <StatCard label="Niveau" value={current.name} icon={TrendingUp} hint={current.perk} />
        <StatCard
          label="Prochain niveau"
          value={next ? next.name : "Max"}
          icon={TrendingUp}
          hint={next ? `${toNext} points restants` : "Niveau maximal atteint"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Progression</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <Progress value={progress} />
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {TIERS.map((t) => (
                <div
                  key={t.name}
                  className={cn(
                    "rounded-xl border p-3 text-center text-sm",
                    current.name === t.name
                      ? "border-gold bg-gold/10 text-gold"
                      : "border-border text-muted-foreground",
                  )}
                >
                  <p className="font-medium">{t.name}</p>
                  <p className="text-xs">{t.min} pts</p>
                </div>
              ))}
            </div>
          </div>
          <div className="border-t border-border pt-5">
            <p className="mb-3 text-sm font-medium">Échanger mes points</p>
            <RedeemLoyalty points={points} />
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-b border-border p-4">
          <h2 className="font-semibold">Historique des points</h2>
        </div>
        <div className="divide-y divide-border">
          {txns.length === 0 && (
            <p className="p-6 text-center text-sm text-muted-foreground">
              Aucun mouvement de points pour l&apos;instant.
            </p>
          )}
          {txns.map((t) => (
            <div key={t.id} className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium">
                  {t.points > 0 ? "Points gagnés" : "Points échangés"}
                </p>
                <p className="text-xs text-muted-foreground">{formatDateTime(t.createdAt)}</p>
              </div>
              <span
                className={cn(
                  "font-semibold",
                  t.points > 0 ? "text-emerald-400" : "text-amber-400",
                )}
              >
                {t.points > 0 ? "+" : ""}
                {t.points}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
