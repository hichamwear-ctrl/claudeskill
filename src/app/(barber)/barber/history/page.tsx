import type { Metadata } from "next";
import { History } from "lucide-react";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { StatusBadge } from "@/components/status-badge";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Historique" };
export const dynamic = "force-dynamic";

export default async function BarberHistoryPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const past = await prisma.reservation.findMany({
    where: { barberId: barber.id, status: { in: ["TERMINEE", "ANNULEE"] } },
    include: { persons: true, address: true },
    orderBy: { scheduledAt: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Historique" subtitle="Vos prestations passées." />
      {past.length === 0 ? (
        <EmptyState icon={History} title="Aucune prestation passée" />
      ) : (
        <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {past.map((r) => (
            <div key={r.id} className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className="text-sm font-medium">{formatDateTime(r.scheduledAt)}</p>
                <p className="text-xs text-muted-foreground">
                  {r.persons.map((p) => SERVICES[p.service].name).join(", ")} ·{" "}
                  {r.address.city}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm font-semibold text-gold">
                  {formatCurrency(r.total)}
                </span>
                <StatusBadge status={r.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
