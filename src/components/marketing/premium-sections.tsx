"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  Home,
  ShieldCheck,
  Clock,
  Sparkles,
  Wallet,
  Star,
  Check,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Media } from "@/components/media";
import { SectionHeading } from "@/components/marketing/section-heading";
import { BENEFITS, TESTIMONIALS, type Benefit } from "@/lib/marketing-content";
import { SERVICE_LIST } from "@/lib/pricing";
import { formatCurrency, formatDuration } from "@/lib/utils";

const BENEFIT_ICONS: Record<Benefit["icon"], LucideIcon> = {
  home: Home,
  shield: ShieldCheck,
  clock: Clock,
  sparkles: Sparkles,
  wallet: Wallet,
  star: Star,
};

function useReveal() {
  const reduce = useReducedMotion();
  return {
    initial: reduce ? { opacity: 1 } : { opacity: 0, y: 24 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px" },
  };
}

// --- Benefits ----------------------------------------------------------------
export function BenefitsSection() {
  const reveal = useReveal();
  return (
    <section className="py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Pourquoi Barber Home"
          title={<>Le soin d&apos;un salon, le confort de chez vous</>}
          subtitle="Une expérience pensée pour être simple, fiable et haut de gamme, du premier clic à la dernière retouche."
        />
        <div className="mt-14 grid gap-8 lg:grid-cols-2 lg:items-center">
          <div className="grid gap-4 sm:grid-cols-2">
            {BENEFITS.map((b, i) => {
              const Icon = BENEFIT_ICONS[b.icon];
              return (
                <motion.div
                  key={b.title}
                  {...reveal}
                  transition={{ duration: 0.5, delay: i * 0.05 }}
                  className="glass rounded-2xl p-5 transition-colors hover:border-gold/30"
                >
                  <div className="mb-3 flex size-10 items-center justify-center rounded-xl bg-gold/10 text-gold">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="font-semibold">{b.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{b.text}</p>
                </motion.div>
              );
            })}
          </div>
          <motion.div {...reveal} transition={{ duration: 0.6 }} className="relative">
            <Media image="shopScene" className="gold-glow" />
            <div className="glass absolute -bottom-5 -left-5 hidden rounded-2xl px-5 py-4 premium-shadow sm:block">
              <p className="font-display text-2xl font-bold text-gold-gradient">4,9/5</p>
              <p className="text-xs text-muted-foreground">+2 500 prestations</p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// --- Pricing -----------------------------------------------------------------
export function PricingSection() {
  const reveal = useReveal();
  return (
    <section id="tarifs" className="border-y border-border/60 bg-secondary/20 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Tarifs"
          title="Des prix clairs, sans abonnement"
          subtitle="Vous voyez le total avant de confirmer. Un supplément déplacement s'applique uniquement hors de Bruxelles."
        />
        <div className="mx-auto mt-14 grid max-w-4xl gap-5 md:grid-cols-3">
          {SERVICE_LIST.map((s, i) => {
            const featured = s.key === "ADULTE_COUPE_BARBE";
            return (
              <motion.div
                key={s.key}
                {...reveal}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className={
                  "relative flex flex-col rounded-2xl border p-6 premium-shadow " +
                  (featured
                    ? "border-gold/40 bg-gold/[0.04] gold-glow"
                    : "border-border bg-card")
                }
              >
                {featured && (
                  <span className="absolute -top-3 left-6 rounded-full bg-gold-gradient px-3 py-0.5 text-xs font-semibold text-black">
                    Le plus choisi
                  </span>
                )}
                <h3 className="text-lg font-semibold">{s.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {s.type === "ENFANT" ? "Pour les enfants" : "Pour adultes"}
                </p>
                <div className="mt-6 flex items-end gap-1">
                  <span className="font-display text-4xl font-bold text-gold-gradient">
                    {formatCurrency(s.price)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Durée ≈ {formatDuration(s.duration)}
                </p>
                <ul className="mt-5 space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <Check className="size-4 text-gold" /> À domicile
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="size-4 text-gold" /> Matériel pro & hygiène
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="size-4 text-gold" /> Barber vérifié
                  </li>
                </ul>
                <Button
                  asChild
                  variant={featured ? "default" : "secondary"}
                  className="mt-6 w-full"
                >
                  <Link href="/register">Réserver</Link>
                </Button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// --- Testimonials ------------------------------------------------------------
export function TestimonialsSection() {
  const reveal = useReveal();
  return (
    <section className="py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Ils nous font confiance"
          title="Une expérience qui fait l'unanimité"
        />
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {TESTIMONIALS.map((t, i) => (
            <motion.figure
              key={t.name}
              {...reveal}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="glass flex flex-col rounded-2xl p-6"
            >
              <div className="mb-3 flex gap-1 text-gold" aria-label={`${t.rating} sur 5`}>
                {Array.from({ length: t.rating }).map((_, j) => (
                  <Star key={j} className="size-4 fill-current" />
                ))}
              </div>
              <blockquote className="flex-1 text-sm text-foreground/90">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-5 flex items-center gap-3">
                <span
                  aria-hidden
                  className="flex size-10 items-center justify-center rounded-full bg-gold-gradient text-sm font-semibold text-black"
                >
                  {t.name.split(" ").map((w) => w[0]).join("")}
                </span>
                <div>
                  <p className="text-sm font-medium">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.role}</p>
                </div>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}

// --- Final CTA ---------------------------------------------------------------
export function FinalCta() {
  return (
    <section className="py-24">
      <div className="container">
        <div className="glass gold-glow relative overflow-hidden rounded-3xl px-8 py-16 text-center premium-shadow">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-gold/5 blur-3xl" />
          <h2 className="mx-auto max-w-2xl font-display text-4xl font-bold tracking-tight sm:text-5xl">
            Prêt pour une coupe <span className="text-gold-gradient">sans bouger</span> ?
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
            Créez votre compte et réservez votre premier barber à domicile en moins
            de deux minutes.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button size="lg" asChild>
              <Link href="/register">
                Créer mon compte <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/login">J&apos;ai déjà un compte</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
