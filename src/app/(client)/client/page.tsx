import Link from "next/link";
import {
  CalendarPlus,
  CalendarCheck,
  Wallet,
  Sparkles,
  CalendarClock,
} from "lucide-react";
import { requireRole } from "@/lib/session";
import { getClientDashboard } from "@/lib/reservations";
import { Button } from "@/components/ui/button";
import { PageHeader, StatCard, EmptyState } from "@/components/dashboard/common";
import { ReservationCard } from "@/components/dashboard/reservation-card";
import { StatusTracker } from "@/components/dashboard/status-tracker";
import { CancelReservationButton } from "@/components/dashboard/reservation-actions";
import { AutoRefresh } from "@/components/dashboard/auto-refresh";
import { StatusBadge } from "@/components/status-badge";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ClientDashboardPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const { active, history, stats } = await getClientDashboard(session.user.id);

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <AutoRefresh />
      <PageHeader
        title={`Bonjour ${session.user.firstName} 👋`}
        subtitle="Voici un aperçu de vos réservations."
        action={
          <Button asChild>
            <Link href="/client/book">
              <CalendarPlus className="size-4" />
              Nouvelle réservation
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Réservations"
          value={stats.totalReservations}
          icon={CalendarCheck}
          hint="Prestations terminées"
        />
        <StatCard
          label="Montant dépensé"
          value={formatCurrency(stats.totalSpent)}
          icon={Wallet}
        />
        <StatCard
          label="En cours"
          value={active.length}
          icon={Sparkles}
          accent
          hint="Réservations actives"
        />
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Réservation en cours</h2>
        {active.length === 0 ? (
          <EmptyState
            icon={CalendarClock}
            title="Aucune réservation en cours"
            description="Réservez un barber à domicile en quelques secondes."
            action={
              <Button asChild>
                <Link href="/client/book">Réserver maintenant</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-4">
            {active.map((r) => (
              <ReservationCard key={r.id} reservation={r}>
                <StatusTracker status={r.status} />
                <div className="mt-4 flex justify-end">
                  <CancelReservationButton
                    id={r.id}
                    status={r.status}
                  />
                </div>
              </ReservationCard>
            ))}
          </div>
        )}
      </section>

      {history.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Historique récent</h2>
            <Button variant="link" size="sm" asChild>
              <Link href="/client/history">Tout voir</Link>
            </Button>
          </div>
          <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
            {history.slice(0, 5).map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between gap-4 p-4"
              >
                <div>
                  <p className="text-sm font-medium">
                    {formatDateTime(r.scheduledAt)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {r.persons.length} personne(s)
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
        </section>
      )}
    </div>
  );
}
