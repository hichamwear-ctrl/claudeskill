import type { Metadata } from "next";
import { Tag } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Promotions" };
export const dynamic = "force-dynamic";

export default async function AdminPromosPage() {
  await requireRole(["ADMIN"]);
  const promos = await prisma.promoCode.findMany({
    orderBy: { createdAt: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Promotions"
        subtitle="Codes de réduction disponibles."
      />
      {promos.length === 0 ? (
        <EmptyState icon={Tag} title="Aucune promotion" description="Créez des codes promo pour vos campagnes." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {promos.map((p) => (
            <Card key={p.id} className="p-5">
              <div className="flex items-center justify-between">
                <span className="rounded-lg bg-gold/10 px-3 py-1 font-mono text-sm font-bold text-gold">
                  {p.code}
                </span>
                <Badge
                  className={
                    p.active
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-400"
                      : "border-border bg-secondary text-muted-foreground"
                  }
                >
                  {p.active ? "Actif" : "Inactif"}
                </Badge>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{p.description}</p>
              <p className="mt-2 font-semibold">
                {p.percentOff
                  ? `-${p.percentOff}%`
                  : p.amountOff
                    ? `-${formatCurrency(p.amountOff)}`
                    : "—"}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Utilisé {p.usedCount}
                {p.maxUses ? `/${p.maxUses}` : ""} fois
                {p.expiresAt ? ` · expire le ${formatDate(p.expiresAt)}` : ""}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
