import { create } from "zustand";
import type { ServiceKey, PersonType } from "@prisma/client";
import { resolveZone } from "@/lib/zones";

export interface BookingAddress {
  addressId?: string;
  label: string;
  street: string;
  number: string;
  city: string;
  postalCode: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
}

export interface BookingPersonDraft {
  id: string;
  type: PersonType;
  service: ServiceKey;
}

interface BookingState {
  step: number;
  address: BookingAddress | null;
  insideZone: boolean;
  scheduledDate: string; // yyyy-mm-dd
  scheduledTime: string; // HH:mm
  persons: BookingPersonDraft[];
  notes: string;
  digicode: string;
  floor: string;
  parking: string;
  paymentMethod: "ONLINE" | "ON_SITE";
  promoCode: string;

  setStep: (step: number) => void;
  next: () => void;
  prev: () => void;
  setAddress: (address: BookingAddress) => void;
  setDateTime: (date: string, time: string) => void;
  addPerson: (type: PersonType) => void;
  updatePerson: (id: string, service: ServiceKey) => void;
  removePerson: (id: string) => void;
  setDetails: (
    details: Partial<
      Pick<BookingState, "notes" | "digicode" | "floor" | "parking">
    >,
  ) => void;
  setPaymentMethod: (m: "ONLINE" | "ON_SITE") => void;
  setPromoCode: (code: string) => void;
  reset: () => void;
}

const initialState = {
  step: 1,
  address: null as BookingAddress | null,
  insideZone: true,
  scheduledDate: "",
  scheduledTime: "",
  persons: [] as BookingPersonDraft[],
  notes: "",
  digicode: "",
  floor: "",
  parking: "",
  paymentMethod: "ON_SITE" as const,
  promoCode: "",
};

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

export const useBookingStore = create<BookingState>((set) => ({
  ...initialState,

  setStep: (step) => set({ step }),
  next: () => set((s) => ({ step: Math.min(5, s.step + 1) })),
  prev: () => set((s) => ({ step: Math.max(1, s.step - 1) })),

  setAddress: (address) =>
    set(() => {
      const { insideZone } = resolveZone({
        postalCode: address.postalCode,
        latitude: address.latitude,
        longitude: address.longitude,
      });
      return { address, insideZone };
    }),

  setDateTime: (scheduledDate, scheduledTime) =>
    set({ scheduledDate, scheduledTime }),

  addPerson: (type) =>
    set((s) => ({
      persons: [
        ...s.persons,
        {
          id: uid(),
          type,
          service: type === "ADULTE" ? "ADULTE_COUPE" : "ENFANT_COUPE",
        },
      ],
    })),

  updatePerson: (id, service) =>
    set((s) => ({
      persons: s.persons.map((p) => (p.id === id ? { ...p, service } : p)),
    })),

  removePerson: (id) =>
    set((s) => ({ persons: s.persons.filter((p) => p.id !== id) })),

  setDetails: (details) => set(details),
  setPaymentMethod: (paymentMethod) => set({ paymentMethod }),
  setPromoCode: (promoCode) => set({ promoCode }),

  reset: () => set(initialState),
}));
