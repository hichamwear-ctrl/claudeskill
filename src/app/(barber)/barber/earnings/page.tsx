import type { Metadata } from "next";
import { Wallet, TrendingUp, Scissors, Star } from "lucide-react";
import { requireRole } from "@/lib/session";
import { ensureBarberProfile } from "@/lib/barber";
import { prisma } from "@/lib/prisma";
import { PageHeader, StatCard } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { formatCurrency, formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Revenus" };
export const dynamic = "force-dynamic";

export default async function EarningsPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);

  const startOfMonth = new Date();
  startOfMonth.setDate(1);
  startOfMonth.setHours(0, 0, 0, 0);

  const [all, month, jobs] = await Promise.all([
    prisma.reservation.aggregate({
      where: { barberId: barber.id, status: "TERMINEE" },
      _sum: { total: true },
    }),
    prisma.reservation.aggregate({
      where: {
        barberId: barber.id,
        status: "TERMINEE",
        scheduledAt: { gte: startOfMonth },
      },
      _sum: { total: true },
    }),
    prisma.reservation.findMany({
      where: { barberId: barber.id, status: "TERMINEE" },
      orderBy: { scheduledAt: "desc" },
      take: 10,
      include: { client: true },
    }),
  ]);

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Revenus" subtitle="Suivez vos gains." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Revenus totaux" value={formatCurrency(all._sum.total ?? 0)} icon={Wallet} accent />
        <StatCard label="Ce mois-ci" value={formatCurrency(month._sum.total ?? 0)} icon={TrendingUp} />
        <StatCard label="Prestations" value={barber.totalJobs} icon={Scissors} />
        <StatCard label="Note" value={barber.rating.toFixed(1)} icon={Star} />
      </div>

      <Card className="overflow-hidden">
        <div className="border-b border-border p-4">
          <h2 className="font-semibold">Dernières prestations rémunérées</h2>
        </div>
        <div className="divide-y divide-border">
          {jobs.length === 0 && (
            <p className="p-6 text-center text-sm text-muted-foreground">
              Aucune prestation rémunérée pour l&apos;instant.
            </p>
          )}
          {jobs.map((j) => (
            <div key={j.id} className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium">
                  {j.client.firstName} {j.client.lastName}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(j.scheduledAt)}
                </p>
              </div>
              <span className="font-semibold text-gold">
                {formatCurrency(j.total)}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
