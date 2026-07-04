"use client";

import { motion } from "framer-motion";
import {
  MapPin,
  CalendarClock,
  Users,
  ShieldCheck,
  Scissors,
  Sparkles,
  Home,
  BadgeEuro,
} from "lucide-react";
import { SERVICE_LIST } from "@/lib/pricing";
import { formatCurrency, formatDuration } from "@/lib/utils";

const reveal = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

export function ServicesSection() {
  return (
    <section id="services" className="py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Nos prestations"
          title="Un service, plusieurs styles"
          subtitle="Des tarifs transparents. Aucun frais caché — un supplément déplacement s'applique uniquement hors de Bruxelles."
        />
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {SERVICE_LIST.map((s, i) => (
            <motion.div
              key={s.key}
              variants={reveal}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-80px" }}
              transition={{ delay: i * 0.08 }}
              className="glass group rounded-2xl p-6 transition-all hover:border-gold/30"
            >
              <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-gold/10 text-gold transition-transform group-hover:scale-110">
                <Scissors className="size-6" />
              </div>
              <h3 className="text-xl font-semibold">{s.name}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {s.type === "ENFANT" ? "Pour les enfants" : "Pour adultes"}
              </p>
              <div className="mt-6 flex items-end justify-between">
                <span className="text-3xl font-bold text-gold-gradient">
                  {formatCurrency(s.price)}
                </span>
                <span className="text-sm text-muted-foreground">
                  {formatDuration(s.duration)}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
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
    text: "Choisissez un créneau parmi les disponibilités en temps réel.",
  },
  {
    icon: Users,
    title: "Vos personnes",
    text: "Ajoutez adultes et enfants, chacun avec sa prestation.",
  },
  {
    icon: Sparkles,
    title: "Le barber arrive",
    text: "Suivez votre barber en direct, de la demande à la prestation.",
  },
];

export function HowSection() {
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
              variants={reveal}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-80px" }}
              transition={{ delay: i * 0.08 }}
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
        <motion.div
          variants={reveal}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="glass relative aspect-square overflow-hidden rounded-3xl p-1 premium-shadow"
        >
          <div className="noise-bg flex h-full w-full items-center justify-center rounded-[22px] bg-secondary/40">
            <div className="text-center">
              <div className="mx-auto flex size-20 items-center justify-center rounded-full bg-gold-gradient text-black gold-glow">
                <MapPin className="size-9" />
              </div>
              <p className="mt-4 font-display text-2xl font-bold">Bruxelles</p>
              <p className="text-sm text-muted-foreground">
                50.85° N, 4.35° E
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  align?: "center" | "left";
}) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-xl"}>
      <p className="text-sm font-semibold uppercase tracking-widest text-gold">
        {eyebrow}
      </p>
      <h2 className="mt-3 font-display text-4xl font-bold tracking-tight sm:text-5xl">
        {title}
      </h2>
      {subtitle && <p className="mt-4 text-muted-foreground">{subtitle}</p>}
    </div>
  );
}
