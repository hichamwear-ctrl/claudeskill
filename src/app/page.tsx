import dynamic from "next/dynamic";
import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Hero } from "@/components/marketing/hero";
import { HowSection, ZoneSection } from "@/components/marketing/sections";
import {
  BenefitsSection,
  PricingSection,
} from "@/components/marketing/premium-sections";
import { FAQ } from "@/lib/marketing-content";

// Below-the-fold: code-split (still server-rendered for SEO).
const TestimonialsSection = dynamic(() =>
  import("@/components/marketing/premium-sections").then((m) => m.TestimonialsSection),
);
const FaqSection = dynamic(() =>
  import("@/components/marketing/faq").then((m) => m.FaqSection),
);
const FinalCta = dynamic(() =>
  import("@/components/marketing/premium-sections").then((m) => m.FinalCta),
);

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "LocalBusiness",
      name: "Barber Home",
      description:
        "Le barber premium à domicile à Bruxelles. Coupe, barbe et coupe enfant.",
      areaServed: { "@type": "City", name: "Bruxelles" },
      priceRange: "€€",
      serviceType: "Barber à domicile",
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: "4.9",
        reviewCount: "2500",
      },
    },
    {
      "@type": "FAQPage",
      mainEntity: FAQ.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <SiteHeader />
      <main id="main">
        <Hero />
        <BenefitsSection />
        <HowSection />
        <PricingSection />
        <ZoneSection />
        <TestimonialsSection />
        <FaqSection />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  );
}
