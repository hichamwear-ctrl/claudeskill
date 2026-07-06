import Link from "next/link";
import { CalendarCheck, Wallet, Sparkles, CalendarClock } from "lucide-react";
import { requireRole } from "@/server/session";
import { getClientDashboard } from "@/server/reservations";
import { Button } from "@/components/ui/button";
import { StatCard, EmptyState } from "@/components/dashboard/common";
import { WelcomeBanner } from "@/components/dashboard/welcome-banner";
import { ReservationCard } from "@/components/dashboard/reservation-card";
import { StatusTracker } from "@/components/dashboard/status-tracker";
import { CancelReservationButton } from "@/components/dashboard/reservation-actions";
import { ReservationRefresher } from "@/components/realtime/reservation-refresher";
import { ClientTracking } from "@/components/tracking/client-tracking";
import { StatusBadge } from "@/components/status-badge";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ClientDashboardPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const { active, history, stats } = await getClientDashboard(session.user.id);

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <ReservationRefresher ids={active.map((r) => r.id)} />
      <WelcomeBanner firstName={session.user.firstName} />

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
                {(r.status === "EN_ROUTE" || r.status === "ARRIVE") &&
                  r.address.latitude != null &&
                  r.address.longitude != null && (
                    <div className="mt-4">
                      <ClientTracking
                        reservationId={r.id}
                        clientPoint={{
                          lat: r.address.latitude,
                          lng: r.address.longitude,
                        }}
                        initialBarberPoint={
                          r.barber?.currentLat != null && r.barber?.currentLng != null
                            ? { lat: r.barber.currentLat, lng: r.barber.currentLng }
                            : null
                        }
                      />
                    </div>
                  )}
                {r.status === "ACCEPTEE" && (
                  <div className="mt-4 rounded-xl border border-gold/30 bg-gold/10 px-4 py-3 text-sm text-gold">
                    Un barber a accepté votre demande — ouvrez la commande pour
                    voir son profil et confirmer.
                  </div>
                )}
                <div className="mt-4 flex items-center justify-between gap-2">
                  <Button variant="secondary" size="sm" asChild>
                    <Link href={`/client/orders/${r.id}`}>Gérer la commande</Link>
                  </Button>
                  <CancelReservationButton id={r.id} status={r.status} />
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
