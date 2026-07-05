import type { Metadata } from "next";
import Link from "next/link";
import { ReceiptText, Download, RotateCcw } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ReviewForm } from "@/components/dashboard/review-form";
import { FavoriteButton } from "@/components/dashboard/favorite-button";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Historique & factures" };
export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const [reservations, favorites] = await Promise.all([
    prisma.reservation.findMany({
      where: { clientId: session.user.id, status: { in: ["TERMINEE", "ANNULEE"] } },
      include: {
        persons: true,
        address: true,
        invoice: true,
        review: true,
        barber: { include: { user: true } },
      },
      orderBy: { scheduledAt: "desc" },
    }),
    prisma.favorite.findMany({
      where: { userId: session.user.id },
      select: { barberId: true },
    }),
  ]);
  const favoriteIds = new Set(favorites.map((f) => f.barberId));

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Historique & factures"
        subtitle="Retrouvez toutes vos prestations passées."
      />

      {reservations.length === 0 ? (
        <EmptyState
          icon={ReceiptText}
          title="Aucune prestation passée"
          description="Vos réservations terminées apparaîtront ici."
          action={
            <Button asChild>
              <Link href="/client/book">Réserver</Link>
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {reservations.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <p className="font-medium">{formatDateTime(r.scheduledAt)}</p>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {r.persons.map((p) => SERVICES[p.service].name).join(", ")} ·{" "}
                    {r.address.postalCode} {r.address.city}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-display text-lg font-bold text-gold">
                    {formatCurrency(r.total)}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button variant="secondary" size="sm" asChild>
                  <a href={`/api/invoices/${r.id}/pdf`} target="_blank" rel="noreferrer">
                    <Download className="size-4" />
                    Facture PDF
                  </a>
                </Button>
                <Button variant="secondary" size="sm" asChild>
                  <Link href="/client/book">
                    <RotateCcw className="size-4" />
                    Réserver à nouveau
                  </Link>
                </Button>
                {r.status === "TERMINEE" && r.barberId && (
                  <FavoriteButton
                    barberId={r.barberId}
                    initialFavorited={favoriteIds.has(r.barberId)}
                    showLabel
                  />
                )}
              </div>

              {r.status === "TERMINEE" && !r.review && (
                <div className="mt-4 border-t border-border pt-4">
                  <ReviewForm reservationId={r.id} />
                </div>
              )}
              {r.review && (
                <div className="mt-4 border-t border-border pt-4 text-sm">
                  <p className="text-muted-foreground">
                    Votre note :{" "}
                    <span className="text-gold">
                      {"★".repeat(r.review.rating)}
                      {"☆".repeat(5 - r.review.rating)}
                    </span>
                  </p>
                  {r.review.comment && (
                    <p className="mt-1 italic">&ldquo;{r.review.comment}&rdquo;</p>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
