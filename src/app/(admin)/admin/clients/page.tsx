import type { Metadata } from "next";
import { requireRole } from "@/lib/session";
import { prisma } from "@/lib/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Clients" };
export const dynamic = "force-dynamic";

export default async function AdminClientsPage() {
  await requireRole(["ADMIN"]);
  const clients = await prisma.user.findMany({
    where: { role: "CLIENT" },
    include: { _count: { select: { reservations: true } } },
    orderBy: { createdAt: "desc" },
    take: 100,
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Clients" subtitle={`${clients.length} client(s).`} />
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-4">Client</th>
                <th className="p-4">Email</th>
                <th className="p-4">Téléphone</th>
                <th className="p-4 text-center">Réservations</th>
                <th className="p-4">Inscrit le</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {clients.map((c) => (
                <tr key={c.id} className="hover:bg-secondary/30">
                  <td className="p-4 font-medium">
                    {c.firstName} {c.lastName}
                  </td>
                  <td className="p-4 text-muted-foreground">{c.email}</td>
                  <td className="p-4 text-muted-foreground">{c.phone ?? "—"}</td>
                  <td className="p-4 text-center">{c._count.reservations}</td>
                  <td className="p-4 text-muted-foreground">
                    {formatDate(c.createdAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
