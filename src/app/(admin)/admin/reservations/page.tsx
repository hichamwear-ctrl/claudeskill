import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { AdminStatusSelect } from "@/components/dashboard/admin-status-select";
import { Card } from "@/components/ui/card";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Réservations" };
export const dynamic = "force-dynamic";

export default async function AdminReservationsPage() {
  await requireRole(["ADMIN"]);
  const reservations = await prisma.reservation.findMany({
    include: {
      persons: true,
      client: true,
      address: true,
      barber: { include: { user: true } },
    },
    orderBy: { createdAt: "desc" },
    take: 50,
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Réservations"
        subtitle={`${reservations.length} réservation(s) récente(s).`}
      />
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-4">Réf.</th>
                <th className="p-4">Client</th>
                <th className="p-4">Date</th>
                <th className="p-4">Prestations</th>
                <th className="p-4">Barber</th>
                <th className="p-4 text-right">Total</th>
                <th className="p-4">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {reservations.map((r) => (
                <tr key={r.id} className="hover:bg-secondary/30">
                  <td className="p-4 font-mono text-xs">
                    {r.reference.slice(0, 6).toUpperCase()}
                  </td>
                  <td className="p-4">
                    {r.client.firstName} {r.client.lastName}
                  </td>
                  <td className="p-4 text-muted-foreground">
                    {formatDateTime(r.scheduledAt)}
                  </td>
                  <td className="p-4 text-muted-foreground">
                    {r.persons.map((p) => SERVICES[p.service].name).join(", ")}
                  </td>
                  <td className="p-4 text-muted-foreground">
                    {r.barber
                      ? `${r.barber.user.firstName} ${r.barber.user.lastName}`
                      : "—"}
                  </td>
                  <td className="p-4 text-right font-semibold text-gold">
                    {formatCurrency(r.total)}
                  </td>
                  <td className="p-4">
                    <AdminStatusSelect id={r.id} status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
