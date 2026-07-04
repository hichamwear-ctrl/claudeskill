import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { WorkingHoursEditor } from "@/components/dashboard/working-hours-editor";
import { AvailabilityToggle } from "@/components/dashboard/availability-toggle";

export const metadata: Metadata = { title: "Disponibilités" };
export const dynamic = "force-dynamic";

export default async function AvailabilityPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const hours = await prisma.workingHours.findMany({
    where: { barberId: barber.id },
    orderBy: { weekday: "asc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Disponibilités"
        subtitle="Définissez vos jours et horaires de travail."
        action={<AvailabilityToggle initial={barber.isAvailable} />}
      />
      <WorkingHoursEditor initial={hours} />
    </div>
  );
}
