import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { BarberProfileEditor } from "@/components/barber/profile-editor";

export const metadata: Metadata = { title: "Mon profil" };
export const dynamic = "force-dynamic";

export default async function BarberProfilePage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const photos = await prisma.barberPhoto.findMany({
    where: { barberId: barber.id },
    orderBy: { createdAt: "desc" },
    select: { id: true, url: true, caption: true },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Mon profil public"
        subtitle="Ces informations sont visibles par les clients après acceptation."
      />
      <BarberProfileEditor
        initial={{
          bio: barber.bio ?? "",
          yearsExperience: barber.yearsExperience,
          level: barber.level,
          instagram: barber.instagram ?? "",
          snapchat: barber.snapchat ?? "",
          photos,
        }}
      />
    </div>
  );
}
