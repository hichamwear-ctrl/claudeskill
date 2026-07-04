import Link from "next/link";
import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Hero } from "@/components/marketing/hero";
import {
  ServicesSection,
  HowSection,
  ZoneSection,
} from "@/components/marketing/sections";
import { Button } from "@/components/ui/button";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  name: "Barber Home",
  description:
    "Le barber premium à domicile à Bruxelles. Coupe, barbe et coupe enfant.",
  areaServed: { "@type": "City", name: "Bruxelles" },
  priceRange: "€€",
  serviceType: "Barber à domicile",
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <SiteHeader />
      <main>
        <Hero />
        <ServicesSection />
        <HowSection />
        <ZoneSection />

        {/* Final CTA */}
        <section className="py-24">
          <div className="container">
            <div className="glass gold-glow relative overflow-hidden rounded-3xl px-8 py-16 text-center premium-shadow">
              <div className="pointer-events-none absolute inset-0 -z-10 bg-gold/5 blur-3xl" />
              <h2 className="mx-auto max-w-2xl font-display text-4xl font-bold tracking-tight sm:text-5xl">
                Prêt pour une coupe <span className="text-gold-gradient">sans bouger</span> ?
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
                Créez votre compte et réservez votre premier barber à domicile
                en moins de deux minutes.
              </p>
              <div className="mt-8 flex justify-center gap-3">
                <Button size="lg" asChild>
                  <Link href="/register">Créer mon compte</Link>
                </Button>
                <Button size="lg" variant="secondary" asChild>
                  <Link href="/login">Connexion</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
