import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin, Clock } from "lucide-react";
import { requireRole } from "@/server/session";
import { prisma } from "@/server/prisma";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { StatusTracker } from "@/components/dashboard/status-tracker";
import { BarberStatusActions } from "@/components/dashboard/barber-status-actions";
import { BarberTracker } from "@/components/tracking/barber-tracker";
import { OrderConversation } from "@/components/order/conversation";
import { ReservationRefresher } from "@/components/realtime/reservation-refresher";
import { isConversationActive, isGpsActive } from "@/lib/status";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime, formatDuration } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function BarberOrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await requireRole(["BARBER", "ADMIN"]);
  const { id } = await params;

  const reservation = await prisma.reservation.findUnique({
    where: { id },
    include: { persons: true, address: true, client: true, barber: true },
  });
  if (!reservation) notFound();

  // Only the assigned barber (or an admin) may open the order.
  const isAssignedBarber = reservation.barber?.userId === session.user.id;
  if (!isAssignedBarber && session.user.role !== "ADMIN") notFound();

  const { client, address, persons, status } = reservation;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-5 sm:p-8">
      <ReservationRefresher ids={[reservation.id]} />

      <Link
        href="/barber"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Retour
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold">
            {client.firstName} {client.lastName}
          </h1>
          <p className="text-sm text-muted-foreground">
            {formatDateTime(reservation.scheduledAt)}
          </p>
        </div>
        <StatusBadge status={status} />
      </div>

      <Card className="space-y-3 p-5 text-sm">
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 size-4 shrink-0 text-gold" />
          <span>
            {address.street} {address.number}, {address.postalCode} {address.city}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="size-4 text-gold" />
          {formatDuration(reservation.durationMinutes)} ·{" "}
          <span className="text-gold">{formatCurrency(reservation.total)}</span> ·{" "}
          {persons.map((p) => SERVICES[p.service].name).join(", ")}
        </div>
      </Card>

      <Card className="p-5">
        <StatusTracker status={status} />
        <div className="mt-4 border-t border-border pt-4">
          <BarberStatusActions id={reservation.id} status={status} />
        </div>
      </Card>

      {isGpsActive(status) && (
        <Card className="p-5">
          <BarberTracker reservationId={reservation.id} active />
        </Card>
      )}

      {isConversationActive(status) && (
        <OrderConversation
          reservationId={reservation.id}
          currentUserId={session.user.id}
          active
        />
      )}
    </div>
  );
}
