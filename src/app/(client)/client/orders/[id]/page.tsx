import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, PartyPopper, Hourglass } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { getBarberPublicProfile } from "@/server/barber";
import { Card } from "@/components/ui/card";
import { StatusTracker } from "@/components/dashboard/status-tracker";
import { StatusBadge } from "@/components/status-badge";
import { ReservationRefresher } from "@/components/realtime/reservation-refresher";
import { ClientTracking } from "@/components/tracking/client-tracking";
import { BarberProfileCard } from "@/components/barber/profile-card";
import { ConfirmBarberButtons } from "@/components/order/client-actions";
import { OrderConversation } from "@/components/order/conversation";
import { RatingPanel } from "@/components/order/rating-panel";
import { isConversationActive, isGpsActive, isOrderFinished } from "@/lib/status";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ClientOrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  const { id } = await params;

  const reservation = await prisma.reservation.findUnique({
    where: { id },
    include: { persons: true, address: true, review: true, barber: true },
  });
  if (!reservation || reservation.clientId !== session.user.id) notFound();

  const status = reservation.status;
  const profile =
    reservation.barberId && status !== "DEMANDE_ENVOYEE"
      ? await getBarberPublicProfile(reservation.barberId)
      : null;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-5 sm:p-8">
      <ReservationRefresher ids={[reservation.id]} />

      <Link
        href="/client"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Retour
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold">
            Commande {reservation.reference.slice(0, 8).toUpperCase()}
          </h1>
          <p className="text-sm text-muted-foreground">
            {formatDateTime(reservation.scheduledAt)} ·{" "}
            {formatCurrency(reservation.total)}
          </p>
        </div>
        <StatusBadge status={status} />
      </div>

      <Card className="p-5">
        <StatusTracker status={status} />
      </Card>

      {/* En attente d'un barber */}
      {status === "DEMANDE_ENVOYEE" && (
        <Card className="flex items-center gap-3 p-5">
          <Hourglass className="size-5 text-gold" />
          <p className="text-sm text-muted-foreground">
            Votre demande a été transmise aux barbers disponibles. Vous serez
            notifié dès que l&apos;un d&apos;eux accepte.
          </p>
        </Card>
      )}

      {/* Barber a accepté → profil + confirmation */}
      {status === "ACCEPTEE" && profile && (
        <Card className="space-y-5 p-5">
          <div className="flex items-center gap-2 rounded-xl border border-gold/30 bg-gold/10 px-4 py-3 text-sm text-gold">
            <PartyPopper className="size-4 shrink-0" />
            {profile.firstName} {profile.lastName} a accepté votre demande.
            Confirmez pour valider la réservation.
          </div>
          <BarberProfileCard profile={profile} />
          <ConfirmBarberButtons reservationId={reservation.id} />
        </Card>
      )}

      {/* Confirmé → suivi + chat/appels */}
      {isConversationActive(status) && (
        <>
          {isGpsActive(status) &&
            reservation.address.latitude != null &&
            reservation.address.longitude != null && (
              <Card className="p-5">
                <ClientTracking
                  reservationId={reservation.id}
                  clientPoint={{
                    lat: reservation.address.latitude,
                    lng: reservation.address.longitude,
                  }}
                  initialBarberPoint={
                    reservation.barber?.currentLat != null &&
                    reservation.barber?.currentLng != null
                      ? {
                          lat: reservation.barber.currentLat,
                          lng: reservation.barber.currentLng,
                        }
                      : null
                  }
                />
              </Card>
            )}
          <OrderConversation
            reservationId={reservation.id}
            currentUserId={session.user.id}
            active
          />
        </>
      )}

      {/* Arrivé / terminé → notation */}
      {isOrderFinished(status) && (
        <Card className="space-y-4 p-5">
          <div className="flex items-center gap-2 text-sm font-medium">
            <PartyPopper className="size-4 text-gold" />
            Votre barber est arrivé. Merci d&apos;avoir utilisé Barber Home !
          </div>
          {reservation.review ? (
            <p className="text-sm text-muted-foreground">
              Vous avez noté cette prestation {reservation.review.rating}/5. Merci !
            </p>
          ) : (
            <RatingPanel reservationId={reservation.id} />
          )}
        </Card>
      )}
    </div>
  );
}
