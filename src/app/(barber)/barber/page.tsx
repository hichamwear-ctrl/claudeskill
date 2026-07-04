import { CalendarCheck, Wallet, Star, Scissors, Inbox } from "lucide-react";
import { requireRole } from "@/server/session";
import { getBarberDashboard } from "@/server/barber";
import { PageHeader, StatCard, EmptyState } from "@/components/dashboard/common";
import { BarberReservationItem } from "@/components/dashboard/barber-reservation-item";
import { AvailabilityToggle } from "@/components/dashboard/availability-toggle";
import { ReservationRefresher } from "@/components/realtime/reservation-refresher";
import { formatCurrency, greeting } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function BarberDashboardPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const { barber, openRequests, assigned, stats } = await getBarberDashboard(
    session.user.id,
  );

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <ReservationRefresher
        ids={[...openRequests, ...assigned].map((r) => r.id)}
      />
      <PageHeader
        title={`${greeting()} ${session.user.firstName}`}
        subtitle="Gérez vos courses et vos prestations."
        action={<AvailabilityToggle initial={barber.isAvailable} />}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Aujourd'hui" value={stats.today} icon={CalendarCheck} accent />
        <StatCard
          label="Revenus totaux"
          value={formatCurrency(stats.revenue)}
          icon={Wallet}
        />
        <StatCard label="Note moyenne" value={stats.rating.toFixed(1)} icon={Star} />
        <StatCard label="Prestations" value={stats.totalJobs} icon={Scissors} />
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">
          Nouvelles demandes
          {openRequests.length > 0 && (
            <span className="ml-2 rounded-full bg-gold px-2 py-0.5 text-xs text-black">
              {openRequests.length}
            </span>
          )}
        </h2>
        {openRequests.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="Aucune nouvelle demande"
            description="Les nouvelles demandes de réservation apparaîtront ici."
          />
        ) : (
          <div className="grid gap-4">
            {openRequests.map((r) => (
              <BarberReservationItem key={r.id} reservation={r} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Mes courses en cours</h2>
        {assigned.length === 0 ? (
          <EmptyState
            icon={Scissors}
            title="Aucune course active"
            description="Acceptez une demande pour commencer."
          />
        ) : (
          <div className="grid gap-4">
            {assigned.map((r) => (
              <BarberReservationItem key={r.id} reservation={r} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
