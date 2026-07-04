"use client";

import { useState } from "react";
import type { Address } from "@prisma/client";
import { motion } from "framer-motion";
import {
  MapPin,
  Navigation,
  Plus,
  Trash2,
  User,
  Baby,
  Check,
  CalendarDays,
  Info,
} from "lucide-react";
import { useBookingStore } from "@/stores/booking";
import { servicesForType, SERVICES } from "@/lib/pricing";
import { generateSlots, upcomingDays, toDateInput } from "@/lib/slots";
import { formatCurrency, formatDuration, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { usePriceBreakdown } from "@/components/booking/price-summary";

const stepMotion = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  transition: { duration: 0.35 },
};

// ---------------------------------------------------------------------------
// Step 1 — Address
// ---------------------------------------------------------------------------
export function StepAddress({ savedAddresses }: { savedAddresses: Address[] }) {
  const { toast } = useToast();
  const address = useBookingStore((s) => s.address);
  const insideZone = useBookingStore((s) => s.insideZone);
  const setAddress = useBookingStore((s) => s.setAddress);
  const [locating, setLocating] = useState(false);

  const [form, setForm] = useState({
    street: address?.street ?? "",
    number: address?.number ?? "",
    postalCode: address?.postalCode ?? "",
    city: address?.city ?? "Bruxelles",
  });

  function useMyLocation() {
    if (!navigator.geolocation) {
      toast({ variant: "error", title: "Géolocalisation indisponible" });
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        setAddress({
          label: "Ma position",
          street: form.street || "Position GPS",
          number: form.number,
          city: form.city || "Bruxelles",
          postalCode: form.postalCode || "1000",
          country: "Belgique",
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        });
        toast({ variant: "success", title: "Position détectée" });
      },
      () => {
        setLocating(false);
        toast({ variant: "error", title: "Impossible de vous localiser" });
      },
    );
  }

  function selectSaved(a: Address) {
    setAddress({
      addressId: a.id,
      label: a.label,
      street: a.street,
      number: a.number ?? "",
      city: a.city,
      postalCode: a.postalCode,
      country: a.country,
      latitude: a.latitude,
      longitude: a.longitude,
    });
  }

  function saveManual() {
    setAddress({
      label: "Domicile",
      street: form.street,
      number: form.number,
      city: form.city,
      postalCode: form.postalCode,
      country: "Belgique",
      latitude: null,
      longitude: null,
    });
  }

  return (
    <motion.div {...stepMotion} className="space-y-6">
      <StepIntro
        icon={MapPin}
        title="Où souhaitez-vous être coiffé ?"
        subtitle="Utilisez votre position ou saisissez une adresse."
      />

      {savedAddresses.length > 0 && (
        <div className="space-y-2">
          <Label>Adresses enregistrées</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            {savedAddresses.map((a) => (
              <button
                key={a.id}
                onClick={() => selectSaved(a)}
                className={cn(
                  "rounded-xl border p-4 text-left transition-colors",
                  address?.addressId === a.id
                    ? "border-gold bg-gold/10"
                    : "border-border hover:border-gold/40",
                )}
              >
                <p className="text-sm font-medium">{a.label}</p>
                <p className="text-xs text-muted-foreground">
                  {a.street} {a.number}, {a.postalCode} {a.city}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      <Button variant="secondary" onClick={useMyLocation} disabled={locating}>
        <Navigation className={cn("size-4", locating && "animate-pulse")} />
        {locating ? "Localisation…" : "Utiliser ma position"}
      </Button>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Rue</Label>
          <Input
            value={form.street}
            onChange={(e) => setForm({ ...form, street: e.target.value })}
            onBlur={saveManual}
            placeholder="Avenue Louise"
          />
        </div>
        <div className="space-y-1.5">
          <Label>Numéro</Label>
          <Input
            value={form.number}
            onChange={(e) => setForm({ ...form, number: e.target.value })}
            onBlur={saveManual}
            placeholder="12"
          />
        </div>
        <div className="space-y-1.5">
          <Label>Code postal</Label>
          <Input
            value={form.postalCode}
            onChange={(e) => setForm({ ...form, postalCode: e.target.value })}
            onBlur={saveManual}
            placeholder="1050"
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Ville</Label>
          <Input
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            onBlur={saveManual}
            placeholder="Bruxelles"
          />
        </div>
      </div>

      {address && (
        <div
          className={cn(
            "flex items-start gap-3 rounded-xl border px-4 py-3 text-sm",
            insideZone
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-400"
              : "border-amber-400/30 bg-amber-400/10 text-amber-400",
          )}
        >
          <Info className="mt-0.5 size-4 shrink-0" />
          {insideZone ? (
            <span>Adresse dans Bruxelles — aucun supplément déplacement.</span>
          ) : (
            <span>
              Hors zone Bruxelles — un supplément déplacement de{" "}
              {formatCurrency(12)} s&apos;applique.
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Step 2 — Date & time
// ---------------------------------------------------------------------------
export function StepDateTime() {
  const scheduledDate = useBookingStore((s) => s.scheduledDate);
  const scheduledTime = useBookingStore((s) => s.scheduledTime);
  const setDateTime = useBookingStore((s) => s.setDateTime);

  const days = upcomingDays(14);
  const activeDate = scheduledDate || toDateInput(new Date());
  const slots = generateSlots(activeDate);

  return (
    <motion.div {...stepMotion} className="space-y-6">
      <StepIntro
        icon={CalendarDays}
        title="Choisissez un créneau"
        subtitle="Seuls les créneaux disponibles sont affichés."
      />

      <div className="space-y-2">
        <Label>Date</Label>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {days.map((d) => (
            <button
              key={d.value}
              onClick={() => setDateTime(d.value, scheduledTime)}
              className={cn(
                "shrink-0 rounded-xl border px-4 py-3 text-sm capitalize transition-colors",
                activeDate === d.value
                  ? "border-gold bg-gold/10 text-gold"
                  : "border-border hover:border-gold/40",
              )}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Heure</Label>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {slots.map((slot) => (
            <button
              key={slot.time}
              disabled={slot.disabled}
              onClick={() => setDateTime(activeDate, slot.time)}
              className={cn(
                "rounded-lg border py-2.5 text-sm transition-colors",
                slot.disabled && "cursor-not-allowed opacity-30",
                scheduledTime === slot.time && activeDate === scheduledDate
                  ? "border-gold bg-gold/10 text-gold"
                  : "border-border hover:border-gold/40",
              )}
            >
              {slot.time}
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Step 3 — Persons & services
// ---------------------------------------------------------------------------
export function StepPersons() {
  const persons = useBookingStore((s) => s.persons);
  const addPerson = useBookingStore((s) => s.addPerson);
  const updatePerson = useBookingStore((s) => s.updatePerson);
  const removePerson = useBookingStore((s) => s.removePerson);
  const breakdown = usePriceBreakdown();

  return (
    <motion.div {...stepMotion} className="space-y-6">
      <StepIntro
        icon={User}
        title="Qui sera coiffé ?"
        subtitle="Ajoutez autant de personnes que nécessaire."
      />

      <div className="flex gap-3">
        <Button variant="secondary" className="flex-1" onClick={() => addPerson("ADULTE")}>
          <User className="size-4" />
          Ajouter un adulte
        </Button>
        <Button variant="secondary" className="flex-1" onClick={() => addPerson("ENFANT")}>
          <Baby className="size-4" />
          Ajouter un enfant
        </Button>
      </div>

      <div className="space-y-3">
        {persons.length === 0 && (
          <p className="rounded-xl border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
            Aucune personne ajoutée pour l&apos;instant.
          </p>
        )}
        {persons.map((person, index) => {
          const options = servicesForType(person.type);
          return (
            <div key={person.id} className="rounded-2xl border border-border bg-card p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-secondary text-gold">
                    {person.type === "ADULTE" ? (
                      <User className="size-4" />
                    ) : (
                      <Baby className="size-4" />
                    )}
                  </span>
                  <p className="text-sm font-medium">
                    {person.type === "ADULTE" ? "Adulte" : "Enfant"} #{index + 1}
                  </p>
                </div>
                <button
                  onClick={() => removePerson(person.id)}
                  className="text-muted-foreground transition-colors hover:text-rose-400"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {options.map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => updatePerson(person.id, opt.key)}
                    className={cn(
                      "flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors",
                      person.service === opt.key
                        ? "border-gold bg-gold/10"
                        : "border-border hover:border-gold/40",
                    )}
                  >
                    <div>
                      <p className="text-sm font-medium">{opt.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDuration(opt.duration)}
                      </p>
                    </div>
                    <span className="font-semibold text-gold">
                      {formatCurrency(opt.price)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {persons.length > 0 && (
        <div className="flex items-center justify-between rounded-xl bg-secondary/50 px-4 py-3 text-sm">
          <span className="text-muted-foreground">
            {persons.length} personne(s) · {formatDuration(breakdown.durationMinutes)}
          </span>
          <span className="font-semibold">
            Sous-total {formatCurrency(breakdown.subtotal)}
          </span>
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Step 4 — Access details
// ---------------------------------------------------------------------------
export function StepDetails() {
  const store = useBookingStore();

  return (
    <motion.div {...stepMotion} className="space-y-6">
      <StepIntro
        icon={Info}
        title="Informations utiles"
        subtitle="Aidez votre barber à vous trouver facilement."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Digicode</Label>
          <Input
            value={store.digicode}
            onChange={(e) => store.setDetails({ digicode: e.target.value })}
            placeholder="1234"
          />
        </div>
        <div className="space-y-1.5">
          <Label>Étage</Label>
          <Input
            value={store.floor}
            onChange={(e) => store.setDetails({ floor: e.target.value })}
            placeholder="3ème étage"
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Parking</Label>
          <Input
            value={store.parking}
            onChange={(e) => store.setDetails({ parking: e.target.value })}
            placeholder="Parking visiteur disponible"
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Notes</Label>
          <Textarea
            value={store.notes}
            onChange={(e) => store.setDetails({ notes: e.target.value })}
            placeholder="Toute information utile pour votre barber…"
          />
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Step 5 — Summary
// ---------------------------------------------------------------------------
export function StepSummary() {
  const store = useBookingStore();
  const breakdown = usePriceBreakdown();
  const { address, persons, insideZone } = store;

  return (
    <motion.div {...stepMotion} className="space-y-6">
      <StepIntro
        icon={Check}
        title="Vérifiez votre réservation"
        subtitle="Un dernier coup d'œil avant de confirmer."
      />

      <div className="space-y-3">
        <SummaryRow label="Adresse">
          {address
            ? `${address.street} ${address.number}, ${address.postalCode} ${address.city}`
            : "—"}
        </SummaryRow>
        <SummaryRow label="Date & heure">
          {store.scheduledDate
            ? `${store.scheduledDate} à ${store.scheduledTime || "—"}`
            : "—"}
        </SummaryRow>
        <SummaryRow label="Prestations">
          <div className="space-y-1">
            {persons.map((p) => (
              <div key={p.id} className="flex justify-between gap-4">
                <span>{SERVICES[p.service].name}</span>
                <span>{formatCurrency(SERVICES[p.service].price)}</span>
              </div>
            ))}
          </div>
        </SummaryRow>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Sous-total</span>
            <span>{formatCurrency(breakdown.subtotal)}</span>
          </div>
          <div className="mt-1 flex justify-between text-sm">
            <span className="text-muted-foreground">
              Supplément déplacement{insideZone ? "" : " (hors zone)"}
            </span>
            <span>
              {breakdown.travelFee > 0
                ? formatCurrency(breakdown.travelFee)
                : "Offert"}
            </span>
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
            <span className="font-medium">Total</span>
            <span className="font-display text-xl font-bold text-gold">
              {formatCurrency(breakdown.total)}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Mode de paiement</Label>
          <div className="grid grid-cols-2 gap-2">
            {(
              [
                { key: "ON_SITE", label: "Sur place" },
                { key: "ONLINE", label: "En ligne (bientôt)" },
              ] as const
            ).map((m) => (
              <button
                key={m.key}
                onClick={() => store.setPaymentMethod(m.key)}
                className={cn(
                  "rounded-xl border px-4 py-3 text-sm transition-colors",
                  store.paymentMethod === m.key
                    ? "border-gold bg-gold/10 text-gold"
                    : "border-border hover:border-gold/40",
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function StepIntro({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: typeof MapPin;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-gold-gradient text-black">
        <Icon className="size-5" />
      </span>
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-secondary/40 px-4 py-3 sm:flex-row sm:justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="text-sm font-medium sm:max-w-[60%] sm:text-right">
        {children}
      </div>
    </div>
  );
}

export { Plus };
