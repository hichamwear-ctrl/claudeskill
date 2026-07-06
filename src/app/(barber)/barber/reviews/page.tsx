import type { Metadata } from "next";
import { Star } from "lucide-react";
import { requireRole } from "@/server/session";
import { ensureBarberProfile } from "@/server/barber";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { starString } from "@/lib/barber";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Avis reçus" };
export const dynamic = "force-dynamic";

export default async function BarberReviewsPage() {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const barber = await ensureBarberProfile(session.user.id);
  const reviews = await prisma.review.findMany({
    where: { barberId: barber.id },
    orderBy: { createdAt: "desc" },
    include: { author: { select: { firstName: true } } },
  });

  const avg =
    reviews.length > 0
      ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length
      : 0;

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Avis reçus"
        subtitle={
          reviews.length > 0
            ? `Note moyenne ${avg.toFixed(1)}/5 · ${reviews.length} avis`
            : "Vos avis clients apparaîtront ici."
        }
      />

      {reviews.length === 0 ? (
        <EmptyState
          icon={Star}
          title="Aucun avis pour le moment"
          description="Terminez des prestations pour recevoir vos premiers avis."
        />
      ) : (
        <div className="space-y-3">
          {reviews.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex items-center justify-between">
                <span className="font-medium">{r.author.firstName}</span>
                <span className="text-gold">{starString(r.rating)}</span>
              </div>
              {r.comment && (
                <p className="mt-1 text-sm italic text-muted-foreground">
                  &ldquo;{r.comment}&rdquo;
                </p>
              )}
              {r.photo && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={r.photo}
                  alt=""
                  className="mt-2 size-24 rounded-lg object-cover"
                />
              )}
              <p className="mt-2 text-xs text-muted-foreground">
                {formatDate(r.createdAt)}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
