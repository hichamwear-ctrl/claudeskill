import type {
  Address,
  Reservation,
  ReservationPerson,
} from "@prisma/client";
import { MapPin, Clock, Users } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { SERVICES } from "@/lib/pricing";
import {
  formatCurrency,
  formatDateTime,
  formatDuration,
} from "@/lib/utils";

type ReservationWithRelations = Reservation & {
  persons: ReservationPerson[];
  address: Address;
};

export function ReservationCard({
  reservation,
  children,
}: {
  reservation: ReservationWithRelations;
  children?: React.ReactNode;
}) {
  const { address, persons } = reservation;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-border p-5">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            Réf. {reservation.reference.slice(0, 6).toUpperCase()}
          </p>
          <p className="mt-1 font-display text-lg font-semibold">
            {formatDateTime(reservation.scheduledAt)}
          </p>
        </div>
        <StatusBadge status={reservation.status} />
      </div>

      <div className="grid gap-4 p-5 sm:grid-cols-2">
        <InfoRow icon={MapPin} label="Adresse">
          {address.street} {address.number}, {address.postalCode} {address.city}
        </InfoRow>
        <InfoRow icon={Clock} label="Durée">
          {formatDuration(reservation.durationMinutes)}
        </InfoRow>
        <InfoRow icon={Users} label="Personnes">
          {persons.length} · {persons.map((p) => SERVICES[p.service].name).join(", ")}
        </InfoRow>
        <div className="flex items-end justify-between sm:justify-end sm:gap-6">
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="font-display text-xl font-bold text-gold">
              {formatCurrency(reservation.total)}
            </p>
          </div>
        </div>
      </div>

      {children && <div className="border-t border-border p-5">{children}</div>}
    </Card>
  );
}

function InfoRow({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof MapPin;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-gold">
        <Icon className="size-4" />
      </span>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="truncate text-sm font-medium">{children}</p>
      </div>
    </div>
  );
}
