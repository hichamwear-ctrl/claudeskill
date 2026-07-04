import type { Metadata } from "next";
import { requireRole } from "@/lib/session";
import { prisma } from "@/lib/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { BookingWizard } from "@/components/booking/booking-wizard";

export const metadata: Metadata = { title: "Nouvelle réservation" };
export const dynamic = "force-dynamic";

export default async function BookPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const addresses = await prisma.address.findMany({
    where: { userId: session.user.id },
    orderBy: { isDefault: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Nouvelle réservation"
        subtitle="Réservez votre barber à domicile en 5 étapes."
      />
      <BookingWizard addresses={addresses} />
    </div>
  );
}
