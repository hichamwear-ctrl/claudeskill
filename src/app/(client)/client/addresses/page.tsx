import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { AddressManager } from "@/components/dashboard/address-manager";

export const metadata: Metadata = { title: "Mes adresses" };
export const dynamic = "force-dynamic";

export default async function AddressesPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const addresses = await prisma.address.findMany({
    where: { userId: session.user.id },
    orderBy: { isDefault: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Mes adresses"
        subtitle="Gérez vos adresses de prestation."
      />
      <AddressManager addresses={addresses} />
    </div>
  );
}
