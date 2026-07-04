import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { ProfileForm } from "@/components/dashboard/profile-form";

export const metadata: Metadata = { title: "Profil" };
export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const session = await requireRole(["CLIENT", "BARBER", "ADMIN"]);
  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
  });
  if (!user) return null;

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Mon profil" subtitle="Gérez vos informations personnelles." />
      <ProfileForm
        initial={{
          firstName: user.firstName,
          lastName: user.lastName,
          username: user.username ?? "",
          phone: user.phone ?? "",
          email: user.email,
          image: user.image ?? "",
        }}
      />
    </div>
  );
}
