"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  MapPin,
  CalendarClock,
  Users,
  ShieldCheck,
  Sparkles,
  Home,
  BadgeEuro,
} from "lucide-react";
import { Media } from "@/components/media";
import { SectionHeading } from "@/components/marketing/section-heading";

function useReveal() {
  const reduce = useReducedMotion();
  return {
    initial: reduce ? { opacity: 1 } : { opacity: 0, y: 24 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px" as const },
  };
}

const STEPS = [
  {
    icon: MapPin,
    title: "Votre adresse",
    text: "Géolocalisation ou saisie manuelle. On détecte automatiquement votre zone.",
  },
  {
    icon: CalendarClock,
    title: "Date & heure",
    text: "Choisissez un créneau parmi les disponibilités.",
  },
  {
    icon: Users,
    title: "Vos personnes",
    text: "Ajoutez adultes et enfants, chacun avec sa prestation.",
  },
  {
    icon: Sparkles,
    title: "Le barber arrive",
    text: "Suivez votre réservation, de la demande à la prestation.",
  },
];

export function HowSection() {
  const reveal = useReveal();
  return (
    <section id="how" className="border-y border-border/60 bg-secondary/20 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Comment ça marche"
          title="Réservez en 4 étapes"
          subtitle="Simple comme commander une course. Premium comme un barbershop de luxe."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              {...reveal}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="relative rounded-2xl border border-border bg-card p-6 premium-shadow"
            >
              <span className="absolute right-5 top-5 font-display text-4xl font-bold text-white/5">
                0{i + 1}
              </span>
              <div className="mb-4 flex size-11 items-center justify-center rounded-xl bg-gold-gradient text-black">
                <step.icon className="size-5" />
              </div>
              <h3 className="font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{step.text}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  { icon: Home, title: "À domicile", text: "Le barbershop vient à vous, où que vous soyez." },
  { icon: ShieldCheck, title: "Barbers vérifiés", text: "Des professionnels notés et sélectionnés." },
  { icon: BadgeEuro, title: "Prix transparents", text: "Payez en ligne ou sur place, sans surprise." },
];

export function ZoneSection() {
  const reveal = useReveal();
  return (
    <section id="zone" className="py-24">
      <div className="container grid items-center gap-12 lg:grid-cols-2">
        <div>
          <SectionHeading
            align="left"
            eyebrow="Notre zone"
            title="Bruxelles & alentours"
            subtitle="Nous couvrons les 19 communes de Bruxelles-Capitale. En dehors de la zone, un supplément déplacement transparent est ajouté."
          />
          <div className="mt-8 space-y-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="flex items-start gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gold/10 text-gold">
                  <f.icon className="size-5" />
                </div>
                <div>
                  <p className="font-medium">{f.title}</p>
                  <p className="text-sm text-muted-foreground">{f.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <motion.div {...reveal} transition={{ duration: 0.6 }}>
          <Media image="grooming" className="gold-glow" />
        </motion.div>
      </div>
    </section>
  );
}
