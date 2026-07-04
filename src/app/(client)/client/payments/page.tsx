import type { Metadata } from "next";
import { CreditCard, Download } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PayButton } from "@/components/dashboard/pay-button";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Paiements" };
export const dynamic = "force-dynamic";

const STATUS_STYLE: Record<string, string> = {
  PAID: "border-emerald-400/30 bg-emerald-400/10 text-emerald-400",
  PENDING: "border-amber-400/30 bg-amber-400/10 text-amber-400",
  FAILED: "border-rose-400/30 bg-rose-400/10 text-rose-400",
  REFUNDED: "border-sky-400/30 bg-sky-400/10 text-sky-400",
};

export default async function PaymentsPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const payments = await prisma.payment.findMany({
    where: { reservation: { clientId: session.user.id } },
    include: { reservation: { include: { invoice: true } } },
    orderBy: { createdAt: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Paiements" subtitle="Historique et règlement de vos réservations." />
      {payments.length === 0 ? (
        <EmptyState icon={CreditCard} title="Aucun paiement" description="Vos paiements apparaîtront ici." />
      ) : (
        <div className="space-y-3">
          {payments.map((p) => (
            <Card key={p.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div>
                <p className="font-medium">
                  Réservation {p.reservation.reference.slice(0, 6).toUpperCase()}
                </p>
                <p className="text-sm text-muted-foreground">
                  {formatDateTime(p.createdAt)} ·{" "}
                  {p.method === "ONLINE" ? "En ligne" : "Sur place"}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-display text-lg font-bold text-gold">
                  {formatCurrency(p.amount)}
                </span>
                <Badge className={STATUS_STYLE[p.status] ?? ""}>{p.status}</Badge>
                {p.status === "PAID" ? (
                  <Button variant="secondary" size="sm" asChild>
                    <a href={`/api/invoices/${p.reservationId}`} target="_blank" rel="noreferrer">
                      <Download className="size-4" /> Facture
                    </a>
                  </Button>
                ) : p.method === "ONLINE" && p.status === "PENDING" ? (
                  <PayButton reservationId={p.reservationId} />
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
