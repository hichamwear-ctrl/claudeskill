"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Address } from "@prisma/client";
import { ArrowLeft, ArrowRight, Loader2, Check } from "lucide-react";
import { useBookingStore } from "@/stores/booking";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import { PriceSummary } from "@/components/booking/price-summary";
import {
  StepAddress,
  StepDateTime,
  StepPersons,
  StepDetails,
  StepSummary,
} from "@/components/booking/steps";

const STEPS = ["Adresse", "Créneau", "Personnes", "Détails", "Résumé"];

export function BookingWizard({ addresses }: { addresses: Address[] }) {
  const router = useRouter();
  const { toast } = useToast();
  const store = useBookingStore();
  const [submitting, setSubmitting] = useState(false);

  function canProceed(): boolean {
    switch (store.step) {
      case 1:
        return !!store.address;
      case 2:
        return !!store.scheduledDate && !!store.scheduledTime;
      case 3:
        return store.persons.length > 0;
      default:
        return true;
    }
  }

  function handleNext() {
    if (!canProceed()) {
      toast({
        variant: "error",
        title: "Étape incomplète",
        description: "Veuillez compléter cette étape avant de continuer.",
      });
      return;
    }
    store.next();
  }

  async function submit() {
    if (!store.address) return;
    setSubmitting(true);

    const scheduledAt = new Date(
      `${store.scheduledDate}T${store.scheduledTime}:00`,
    ).toISOString();

    const payload = {
      addressId: store.address.addressId,
      address: store.address.addressId
        ? undefined
        : {
            label: store.address.label,
            street: store.address.street,
            number: store.address.number,
            city: store.address.city,
            postalCode: store.address.postalCode,
            country: store.address.country,
            latitude: store.address.latitude,
            longitude: store.address.longitude,
          },
      scheduledAt,
      persons: store.persons.map((p) => ({ type: p.type, service: p.service })),
      paymentMethod: store.paymentMethod,
      notes: store.notes || undefined,
      digicode: store.digicode || undefined,
      floor: store.floor || undefined,
      parking: store.parking || undefined,
      promoCode: store.promoCode || undefined,
    };

    const res = await fetch("/api/reservations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSubmitting(false);

    if (res.ok) {
      toast({
        variant: "success",
        title: "Réservation envoyée !",
        description: "Votre demande a bien été transmise.",
      });
      store.reset();
      router.push("/client");
      router.refresh();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Échec de la réservation", description: error });
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
      <div>
        {/* Progress steps */}
        <div className="mb-8 flex items-center gap-2">
          {STEPS.map((label, i) => {
            const index = i + 1;
            const active = store.step === index;
            const done = store.step > index;
            return (
              <div key={label} className="flex flex-1 items-center gap-2">
                <div className="flex flex-col items-center gap-1.5">
                  <span
                    className={cn(
                      "flex size-8 items-center justify-center rounded-full border text-xs font-bold transition-colors",
                      done && "border-gold bg-gold text-black",
                      active && "border-gold bg-gold/20 text-gold",
                      !done && !active && "border-border text-muted-foreground",
                    )}
                  >
                    {done ? <Check className="size-4" /> : index}
                  </span>
                  <span
                    className={cn(
                      "hidden text-[11px] sm:block",
                      active ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "h-px flex-1",
                      done ? "bg-gold" : "bg-border",
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Step content */}
        <div className="min-h-[360px]">
          {store.step === 1 && <StepAddress savedAddresses={addresses} />}
          {store.step === 2 && <StepDateTime />}
          {store.step === 3 && <StepPersons />}
          {store.step === 4 && <StepDetails />}
          {store.step === 5 && <StepSummary />}
        </div>

        {/* Navigation */}
        <div className="mt-8 flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={store.prev}
            disabled={store.step === 1}
          >
            <ArrowLeft className="size-4" />
            Retour
          </Button>

          {store.step < 5 ? (
            <Button onClick={handleNext}>
              Continuer
              <ArrowRight className="size-4" />
            </Button>
          ) : (
            <Button onClick={submit} disabled={submitting}>
              {submitting && <Loader2 className="size-4 animate-spin" />}
              Confirmer la réservation
            </Button>
          )}
        </div>
      </div>

      <aside className="hidden lg:block">
        <PriceSummary />
      </aside>
    </div>
  );
}
