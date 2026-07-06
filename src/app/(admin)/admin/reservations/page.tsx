import type { Metadata } from "next";
import { Search } from "lucide-react";
import { requireRole } from "@/server/session";
import { searchReservations } from "@/server/admin";
import { PageHeader } from "@/components/dashboard/common";
import { AdminStatusSelect } from "@/components/dashboard/admin-status-select";
import { Card } from "@/components/ui/card";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Réservations" };
export const dynamic = "force-dynamic";

export default async function AdminReservationsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  await requireRole(["ADMIN"]);
  const { q = "" } = await searchParams;
  const reservations = await searchReservations(q);

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Réservations"
        subtitle={
          q
            ? `${reservations.length} résultat(s) pour « ${q} ».`
            : `${reservations.length} réservation(s) récente(s).`
        }
      />

      {/* Search by order number, client name/firstname, phone, address, barber */}
      <form method="GET" className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            name="q"
            defaultValue={q}
            placeholder="N° commande, nom, prénom, téléphone, adresse, barber…"
            className="h-11 w-full rounded-xl border border-input bg-secondary/50 pl-10 pr-4 text-sm focus-visible:border-gold/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/20"
          />
        </div>
      </form>
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
