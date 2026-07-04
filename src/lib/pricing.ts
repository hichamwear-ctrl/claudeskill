import type { PersonType, ServiceKey } from "@prisma/client";

/**
 * Fixed service catalogue. Prices in EUR, durations in minutes.
 * Kept as pure data so pricing can be computed on client and server identically.
 */
export interface ServiceDefinition {
  key: ServiceKey;
  name: string;
  type: PersonType;
  price: number;
  duration: number;
}

export const SERVICES: Record<ServiceKey, ServiceDefinition> = {
  ADULTE_COUPE: {
    key: "ADULTE_COUPE",
    name: "Coupe",
    type: "ADULTE",
    price: 25,
    duration: 30,
  },
  ADULTE_COUPE_BARBE: {
    key: "ADULTE_COUPE_BARBE",
    name: "Coupe + barbe",
    type: "ADULTE",
    price: 35,
    duration: 45,
  },
  ENFANT_COUPE: {
    key: "ENFANT_COUPE",
    name: "Coupe enfant",
    type: "ENFANT",
    price: 18,
    duration: 25,
  },
};

export const SERVICE_LIST = Object.values(SERVICES);

export function servicesForType(type: PersonType): ServiceDefinition[] {
  return SERVICE_LIST.filter((s) => s.type === type);
}

/** Flat travel supplement applied when the address is outside Brussels. */
export const TRAVEL_FEE_OUTSIDE_BRUSSELS = 12;

export interface BookingPerson {
  type: PersonType;
  service: ServiceKey;
  label?: string;
}

export interface PriceBreakdown {
  subtotal: number;
  travelFee: number;
  discount: number;
  total: number;
  durationMinutes: number;
  lines: Array<{ service: ServiceKey; name: string; price: number; duration: number }>;
}

export function computePrice(
  persons: BookingPerson[],
  opts: { insideZone: boolean; discount?: number } = { insideZone: true },
): PriceBreakdown {
  const lines = persons.map((p) => {
    const def = SERVICES[p.service];
    return { service: p.service, name: def.name, price: def.price, duration: def.duration };
  });

  const subtotal = lines.reduce((sum, l) => sum + l.price, 0);
  const durationMinutes = lines.reduce((sum, l) => sum + l.duration, 0);
  const travelFee = opts.insideZone ? 0 : TRAVEL_FEE_OUTSIDE_BRUSSELS;
  const discount = opts.discount ?? 0;
  const total = Math.max(0, subtotal + travelFee - discount);

  return { subtotal, travelFee, discount, total, durationMinutes, lines };
}
