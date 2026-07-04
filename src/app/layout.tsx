import type { Metadata, Viewport } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const siteUrl = process.env.AUTH_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Barber Home — Le barber premium à domicile à Bruxelles",
    template: "%s · Barber Home",
  },
  description:
    "Réservez un barber professionnel à domicile à Bruxelles. Coupe, barbe, enfants — le luxe du barbershop chez vous, en quelques clics.",
  keywords: [
    "barber",
    "coiffeur à domicile",
    "barbier Bruxelles",
    "coupe homme",
    "barbe",
    "réservation barber",
  ],
  authors: [{ name: "Barber Home" }],
  openGraph: {
    type: "website",
    locale: "fr_BE",
    url: siteUrl,
    siteName: "Barber Home",
    title: "Barber Home — Le barber premium à domicile",
    description:
      "Le Uber des barbers à domicile. Réservez votre barber professionnel à Bruxelles.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Barber Home",
    description: "Le barber premium à domicile à Bruxelles.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={`${inter.variable} ${playfair.variable} dark`}>
      <body className="min-h-screen font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
