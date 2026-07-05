import { prisma } from "./prisma";
import {
  computePrice,
  priceFor,
  isNightHour,
  SERVICES,
  type BookingPerson,
} from "@/lib/pricing";
import { resolveZone } from "@/lib/zones";
import { notifyStatusChange } from "./notifications";
import type { CreateReservationInput } from "@/lib/validations";

/**
 * Creates a reservation for a client, resolving the address (existing or new),
 * computing pricing server-side (never trusting client totals) and persisting
 * the people breakdown.
 */
export async function createReservation(
  clientId: string,
  input: CreateReservationInput,
) {
  // 1. Resolve address
  let addressId = input.addressId;
  let insideZone = true;

  if (!addressId && input.address) {
    const zone = resolveZone({
      postalCode: input.address.postalCode,
      latitude: input.address.latitude,
      longitude: input.address.longitude,
    });
    insideZone = zone.insideZone;
    const created = await prisma.address.create({
      data: {
        userId: clientId,
        label: input.address.label ?? "Domicile",
        street: input.address.street,
        number: input.address.number || null,
        city: input.address.city,
        postalCode: input.address.postalCode,
        country: input.address.country ?? "Belgique",
        latitude: input.address.latitude ?? null,
        longitude: input.address.longitude ?? null,
        insideZone,
      },
    });
    addressId = created.id;
  } else if (addressId) {
    const addr = await prisma.address.findFirst({
      where: { id: addressId, userId: clientId },
    });
    if (!addr) throw new Error("Adresse introuvable");
    insideZone = addr.insideZone;
  } else {
    throw new Error("Aucune adresse fournie");
  }

  // 2. Resolve promo code (optional)
  let discount = 0;
  let promoCodeId: string | undefined;
  if (input.promoCode) {
    const promo = await prisma.promoCode.findUnique({
      where: { code: input.promoCode.toUpperCase() },
    });
    if (
      promo &&
      promo.active &&
      (!promo.expiresAt || promo.expiresAt > new Date()) &&
      (!promo.maxUses || promo.usedCount < promo.maxUses)
    ) {
      promoCodeId = promo.id;
    }
  }

  // 3. Compute pricing server-side (night surcharge derived from the slot hour)
  const scheduledAt = new Date(input.scheduledAt);
  const night = isNightHour(scheduledAt.getHours());
  const persons: BookingPerson[] = input.persons;
  const preBreakdown = computePrice(persons, { insideZone, night });
  if (promoCodeId) {
    const promo = await prisma.promoCode.findUnique({ where: { id: promoCodeId } });
    if (promo?.percentOff) discount = (preBreakdown.subtotal * promo.percentOff) / 100;
    else if (promo?.amountOff) discount = promo.amountOff;
  }
  const breakdown = computePrice(persons, { insideZone, discount, night });

  // 4. Persist reservation + people + payment record
  const reservation = await prisma.reservation.create({
    data: {
      clientId,
      addressId,
      scheduledAt,
      durationMinutes: breakdown.durationMinutes,
      subtotal: breakdown.subtotal,
      travelFee: breakdown.travelFee,
      discount: breakdown.discount,
      total: breakdown.total,
      notes: input.notes,
      digicode: input.digicode,
      floor: input.floor,
      parking: input.parking,
      promoCodeId,
      persons: {
        create: persons.map((p) => ({
          type: p.type,
          service: p.service,
          price: priceFor(p.service, night),
          duration: SERVICES[p.service].duration,
          label: p.label,
        })),
      },
      payment: {
        create: {
          method: input.paymentMethod,
          amount: breakdown.total,
          status: "PENDING",
        },
      },
    },
    include: { persons: true, address: true },
  });

  if (promoCodeId) {
    await prisma.promoCode.update({
      where: { id: promoCodeId },
      data: { usedCount: { increment: 1 } },
    });
  }

  await notifyStatusChange(
    { id: reservation.id, clientId, reference: reservation.reference },
    "DEMANDE_ENVOYEE",
  );

  return reservation;
}

export async function getClientDashboard(clientId: string) {
  const [active, history, aggregates] = await Promise.all([
    prisma.reservation.findMany({
      where: {
        clientId,
        status: { notIn: ["TERMINEE", "ANNULEE"] },
      },
      include: {
        persons: true,
        address: true,
        barber: { include: { user: true } },
      },
      orderBy: { scheduledAt: "asc" },
    }),
    prisma.reservation.findMany({
      where: { clientId, status: { in: ["TERMINEE", "ANNULEE"] } },
      include: { persons: true, address: true, review: true, invoice: true },
      orderBy: { scheduledAt: "desc" },
      take: 20,
    }),
    prisma.reservation.aggregate({
      where: { clientId, status: "TERMINEE" },
      _count: true,
      _sum: { total: true },
    }),
  ]);

  return {
    active,
    history,
    stats: {
      totalReservations: aggregates._count,
      totalSpent: aggregates._sum.total ?? 0,
    },
  };
}
