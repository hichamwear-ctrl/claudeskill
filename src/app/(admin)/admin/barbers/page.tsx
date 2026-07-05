import type { Metadata } from "next";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { formatCurrency, getInitials } from "@/lib/utils";

export const metadata: Metadata = { title: "Barbers" };
export const dynamic = "force-dynamic";

export default async function AdminBarbersPage() {
  await requireRole(["ADMIN"]);
  const barbers = await prisma.barber.findMany({
    include: {
      user: true,
      _count: { select: { reservations: true } },
      reservations: { where: { status: "TERMINEE" }, select: { total: true } },
    },
    orderBy: { rating: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Barbers" subtitle={`${barbers.length} barber(s).`} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {barbers.map((b) => {
          const revenue = b.reservations.reduce((s, r) => s + r.total, 0);
          return (
            <Card key={b.id} className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Avatar className="size-11 rounded-xl">
                    <AvatarImage src="/images/barber-avatar.svg" alt="" />
                    <AvatarFallback className="rounded-xl">
                      {getInitials(b.user.firstName, b.user.lastName)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium">
                      {b.user.firstName} {b.user.lastName}
                    </p>
                    <p className="text-xs text-muted-foreground">{b.user.email}</p>
                  </div>
                </div>
                <Badge
                  className={
                    b.isAvailable
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-400"
                      : "border-border bg-secondary text-muted-foreground"
                  }
                >
                  {b.isAvailable ? "Dispo" : "Indispo"}
                </Badge>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <Metric label="Note" value={b.rating.toFixed(1)} />
                <Metric label="Prestations" value={b.totalJobs} />
                <Metric label="CA" value={formatCurrency(revenue)} />
              </div>
            </Card>
          );
        })}
        {barbers.length === 0 && (
          <p className="text-sm text-muted-foreground">Aucun barber enregistré.</p>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-secondary/50 py-2">
      <p className="text-sm font-semibold">{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}
