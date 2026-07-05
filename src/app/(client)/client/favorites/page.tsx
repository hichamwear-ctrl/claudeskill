import type { Metadata } from "next";
import Link from "next/link";
import { Heart, Star, CalendarPlus } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FavoriteButton } from "@/components/dashboard/favorite-button";
import { getInitials } from "@/lib/utils";

export const metadata: Metadata = { title: "Mes barbers favoris" };
export const dynamic = "force-dynamic";

export default async function FavoritesPage() {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const favorites = await prisma.favorite.findMany({
    where: { userId: session.user.id },
    include: { barber: { include: { user: true } } },
    orderBy: { createdAt: "desc" },
  });

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Mes barbers favoris"
        subtitle="Retrouvez et re-réservez vos barbers préférés."
      />
      {favorites.length === 0 ? (
        <EmptyState
          icon={Heart}
          title="Aucun favori"
          description="Ajoutez un barber en favori depuis votre historique."
          action={
            <Button asChild>
              <Link href="/client/history">Voir mon historique</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {favorites.map((f) => (
            <Card key={f.id} className="p-5">
              <div className="flex items-center gap-3">
                <span className="flex size-12 items-center justify-center rounded-xl bg-gold-gradient font-semibold text-black">
                  {getInitials(f.barber.user.firstName, f.barber.user.lastName)}
                </span>
                <div>
                  <p className="font-medium">
                    {f.barber.user.firstName} {f.barber.user.lastName}
                  </p>
                  <p className="flex items-center gap-1 text-xs text-gold">
                    <Star className="size-3.5 fill-current" />
                    {f.barber.rating.toFixed(1)} · {f.barber.totalJobs} prestations
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <FavoriteButton barberId={f.barberId} initialFavorited showLabel />
                <Button size="sm" asChild>
                  <Link href="/client/book">
                    <CalendarPlus className="size-4" /> Réserver
                  </Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
