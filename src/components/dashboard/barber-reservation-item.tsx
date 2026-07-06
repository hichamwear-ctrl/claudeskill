import type {
  Address,
  Reservation,
  ReservationPerson,
  User,
} from "@prisma/client";
import Link from "next/link";
import { MapPin, Clock, User as UserIcon, KeyRound, MessageSquare } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { BarberStatusActions } from "@/components/dashboard/barber-status-actions";
import { BarberTracker } from "@/components/tracking/barber-tracker";
import { isConversationActive, isGpsActive } from "@/lib/status";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime, formatDuration } from "@/lib/utils";

type Item = Reservation & {
  persons: ReservationPerson[];
  address: Address;
  client: User;
};

export function BarberReservationItem({ reservation }: { reservation: Item }) {
  const { client, address, persons } = reservation;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-gold-gradient font-semibold text-black">
            {client.firstName[0]}
            {client.lastName[0]}
          </span>
          <div>
            <p className="font-medium">
              {client.firstName} {client.lastName}
            </p>
            <p className="text-xs text-muted-foreground">
              {formatDateTime(reservation.scheduledAt)}
            </p>
          </div>
        </div>
        <StatusBadge status={reservation.status} />
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Detail icon={MapPin}>
          {address.street} {address.number}, {address.postalCode} {address.city}
        </Detail>
        <Detail icon={Clock}>
          {formatDuration(reservation.durationMinutes)} ·{" "}
          <span className="text-gold">{formatCurrency(reservation.total)}</span>
        </Detail>
        <Detail icon={UserIcon}>
          {persons.map((p) => SERVICES[p.service].name).join(", ")}
        </Detail>
        {(reservation.digicode || reservation.floor) && (
          <Detail icon={KeyRound}>
            {reservation.digicode && `Digicode ${reservation.digicode}`}
            {reservation.digicode && reservation.floor && " · "}
            {reservation.floor}
          </Detail>
        )}
      </div>

      {reservation.notes && (
        <p className="mt-3 rounded-lg bg-secondary/50 px-3 py-2 text-sm text-muted-foreground">
          {reservation.notes}
        </p>
      )}

      {isGpsActive(reservation.status) && (
        <div className="mt-4">
          <BarberTracker reservationId={reservation.id} active />
        </div>
      )}

      {isConversationActive(reservation.status) && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" asChild>
            <Link href={`/barber/orders/${reservation.id}`}>
              <MessageSquare className="size-4" />
              Ouvrir le chat
            </Link>
          </Button>
        </div>
      )}

      <div className="mt-4 border-t border-border pt-4">
        <BarberStatusActions id={reservation.id} status={reservation.status} />
      </div>
    </Card>
  );
}

function Detail({
  icon: Icon,
  children,
}: {
  icon: typeof MapPin;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2 text-muted-foreground">
      <Icon className="mt-0.5 size-4 shrink-0 text-gold" />
      <span className="text-foreground">{children}</span>
    </div>
  );
}
