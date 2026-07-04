"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, MapPin, Star } from "lucide-react";
import { Button } from "@/components/ui/button";

const fade = {
  hidden: { opacity: 0, y: 20 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.1 * i, duration: 0.6, ease: [0.22, 1, 0.36, 1] },
  }),
};

export function Hero() {
  return (
    <section className="noise-bg relative flex min-h-[92vh] items-center overflow-hidden pt-24">
      {/* Ambient gold glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/3 -z-10 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-gold/10 blur-[120px]" />

      <div className="container grid items-center gap-12 lg:grid-cols-2">
        <div>
          <motion.div
            custom={0}
            variants={fade}
            initial="hidden"
            animate="show"
            className="glass mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium text-gold"
          >
            <MapPin className="size-3.5" />
            Disponible partout à Bruxelles
          </motion.div>

          <motion.h1
            custom={1}
            variants={fade}
            initial="hidden"
            animate="show"
            className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl"
          >
            Le barbershop
            <br />
            <span className="text-gold-gradient">chez vous.</span>
          </motion.h1>

          <motion.p
            custom={2}
            variants={fade}
            initial="hidden"
            animate="show"
            className="mt-6 max-w-md text-lg text-muted-foreground"
          >
            Réservez un barber professionnel à domicile en quelques secondes.
            Coupe, barbe, enfants — l&apos;excellence livrée à votre porte.
          </motion.p>

          <motion.div
            custom={3}
            variants={fade}
            initial="hidden"
            animate="show"
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <Button size="lg" asChild>
              <Link href="/register">
                Réserver maintenant
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/login">J&apos;ai déjà un compte</Link>
            </Button>
          </motion.div>

          <motion.div
            custom={4}
            variants={fade}
            initial="hidden"
            animate="show"
            className="mt-10 flex items-center gap-6"
          >
            <div className="flex -space-x-3">
              {["#D4AF37", "#B8942A", "#E8CE7B", "#8a6d1f"].map((c, i) => (
                <div
                  key={i}
                  className="size-9 rounded-full border-2 border-background"
                  style={{ background: c }}
                />
              ))}
            </div>
            <div>
              <div className="flex items-center gap-1 text-gold">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star key={i} className="size-4 fill-current" />
                ))}
              </div>
              <p className="text-sm text-muted-foreground">
                +2 500 prestations à domicile
              </p>
            </div>
          </motion.div>
        </div>

        {/* Floating premium booking card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 30 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="relative mx-auto w-full max-w-sm"
        >
          <div className="glass gold-glow rounded-3xl p-6 premium-shadow">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Prochaine dispo</p>
              <span className="rounded-full bg-emerald-400/10 px-2.5 py-0.5 text-xs text-emerald-400">
                Aujourd&apos;hui
              </span>
            </div>
            <p className="mt-1 font-display text-3xl font-bold">14:30</p>

            <div className="mt-5 space-y-3">
              {[
                { name: "Coupe", price: "25 €", dur: "30 min" },
                { name: "Coupe + barbe", price: "35 €", dur: "45 min" },
                { name: "Coupe enfant", price: "18 €", dur: "25 min" },
              ].map((s) => (
                <div
                  key={s.name}
                  className="flex items-center justify-between rounded-xl border border-border bg-secondary/40 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{s.name}</p>
                    <p className="text-xs text-muted-foreground">{s.dur}</p>
                  </div>
                  <p className="font-semibold text-gold">{s.price}</p>
                </div>
              ))}
            </div>

            <Button className="mt-5 w-full" asChild>
              <Link href="/register">Choisir un créneau</Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
