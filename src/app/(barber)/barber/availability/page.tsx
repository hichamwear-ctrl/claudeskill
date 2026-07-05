import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { WorkingHoursEditor } from "@/components/dashboard/working-hours-editor";
import { UnavailabilityManager } from "@/components/dashboard/unavailability-manager";
import { AvailabilityToggle } from "@/components/dashboard/availability-toggle";

export const metadata: Metadata = { title: "Disponibilités" };
export const dynamic = "force-dynamic";

export default async function AvailabilityPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const [hours, unavailabilities] = await Promise.all([
    prisma.workingHours.findMany({
      where: { barberId: barber.id },
      orderBy: { weekday: "asc" },
    }),
    prisma.unavailability.findMany({
      where: {
        barberId: barber.id,
        date: { gte: new Date(new Date().setHours(0, 0, 0, 0)) },
      },
      orderBy: { date: "asc" },
    }),
  ]);

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Disponibilités"
        subtitle="Horaires hebdomadaires, congés et indisponibilités ponctuelles."
        action={<AvailabilityToggle initial={barber.isAvailable} />}
      />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Horaires hebdomadaires</h2>
        <WorkingHoursEditor initial={hours} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Congés & indisponibilités</h2>
        <UnavailabilityManager
          initial={unavailabilities.map((u) => ({
            id: u.id,
            date: u.date,
            allDay: u.allDay,
            startTime: u.startTime,
            endTime: u.endTime,
            type: u.type,
            reason: u.reason,
          }))}
        />
      </section>
    </div>
  );
}
