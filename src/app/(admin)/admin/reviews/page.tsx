import type { Metadata } from "next";
import { Star } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Avis" };
export const dynamic = "force-dynamic";

export default async function AdminReviewsPage() {
  await requireRole(["ADMIN"]);
  const reviews = await prisma.review.findMany({
    include: { author: true, barber: { include: { user: true } } },
    orderBy: { createdAt: "desc" },
    take: 50,
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Avis clients" subtitle={`${reviews.length} avis.`} />
      {reviews.length === 0 ? (
        <EmptyState icon={Star} title="Aucun avis" description="Les avis clients apparaîtront ici." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {reviews.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex items-center justify-between">
                <p className="font-medium">
                  {r.author.firstName} {r.author.lastName}
                </p>
                <span className="text-gold">
                  {"★".repeat(r.rating)}
                  {"☆".repeat(5 - r.rating)}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Barber : {r.barber.user.firstName} {r.barber.user.lastName} ·{" "}
                {formatDate(r.createdAt)}
              </p>
              {r.comment && (
                <p className="mt-3 text-sm italic text-muted-foreground">
                  &ldquo;{r.comment}&rdquo;
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
