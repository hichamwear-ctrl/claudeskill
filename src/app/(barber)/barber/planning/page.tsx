import type { Metadata } from "next";
import { CalendarClock } from "lucide-react";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { BarberReservationItem } from "@/components/dashboard/barber-reservation-item";

export const metadata: Metadata = { title: "Planning" };
export const dynamic = "force-dynamic";

export default async function PlanningPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const upcoming = await prisma.reservation.findMany({
    where: {
      barberId: barber.id,
      status: { notIn: ["TERMINEE", "ANNULEE"] },
      scheduledAt: { gte: new Date(new Date().setHours(0, 0, 0, 0)) },
    },
    include: { persons: true, address: true, client: true },
    orderBy: { scheduledAt: "asc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Planning" subtitle="Vos prochaines prestations." />
      {upcoming.length === 0 ? (
        <EmptyState icon={CalendarClock} title="Planning vide" description="Aucune prestation à venir." />
      ) : (
        <div className="grid gap-4">
          {upcoming.map((r) => (
            <BarberReservationItem key={r.id} reservation={r} />
          ))}
        </div>
      )}
    </div>
  );
}
