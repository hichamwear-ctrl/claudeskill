/**
 * Editorial content for the marketing site (Phase 2).
 * Pure data — edit here to change copy without touching components.
 */

export interface Benefit {
  icon: "home" | "shield" | "clock" | "sparkles" | "wallet" | "star";
  title: string;
  text: string;
}

export const BENEFITS: Benefit[] = [
  {
    icon: "home",
    title: "Le barbershop chez vous",
    text: "Plus de salle d'attente. Un barber professionnel se déplace à votre domicile, à l'heure choisie.",
  },
  {
    icon: "shield",
    title: "Barbers vérifiés",
    text: "Chaque barber est sélectionné, noté et évalué après chaque prestation. Qualité garantie.",
  },
  {
    icon: "clock",
    title: "Réservation en 2 minutes",
    text: "Choisissez l'adresse, le créneau et vos prestations. C'est confirmé instantanément.",
  },
  {
    icon: "wallet",
    title: "Tarifs transparents",
    text: "Prix affiché avant de réserver. Paiement sur place ou en ligne, sans surprise.",
  },
  {
    icon: "sparkles",
    title: "Matériel professionnel",
    text: "Hygiène irréprochable et outils haut de gamme pour un résultat digne d'un salon premium.",
  },
  {
    icon: "star",
    title: "Expérience notée 4,9/5",
    text: "Des milliers de prestations à domicile réalisées à Bruxelles, plébiscitées par nos clients.",
  },
];

export interface Testimonial {
  name: string;
  role: string;
  quote: string;
  rating: number;
}

export const TESTIMONIALS: Testimonial[] = [
  {
    name: "Julien M.",
    role: "Ixelles",
    quote:
      "Barber au top, ponctuel et vraiment pro. La coupe est nette, et tout ça sans bouger de chez moi. Je ne reviendrai plus en salon.",
    rating: 5,
  },
  {
    name: "Karim B.",
    role: "Saint-Gilles",
    quote:
      "J'ai réservé pour moi et mes deux fils en même temps. Simple, rapide, et les enfants ont adoré. Service impeccable.",
    rating: 5,
  },
  {
    name: "Thomas D.",
    role: "Uccle",
    quote:
      "Le niveau de finition sur la barbe est bluffant. On sent le vrai savoir-faire. L'appli est claire et élégante.",
    rating: 5,
  },
];

export interface FaqItem {
  q: string;
  a: string;
}

export const FAQ: FaqItem[] = [
  {
    q: "Comment se déroule une réservation ?",
    a: "Vous indiquez votre adresse, choisissez un créneau disponible, ajoutez les personnes et leurs prestations, puis validez. Un barber vous est attribué et vous suivez l'avancement depuis votre espace.",
  },
  {
    q: "Dans quelles zones intervenez-vous ?",
    a: "Nous couvrons les 19 communes de Bruxelles-Capitale. En dehors de cette zone, un supplément déplacement transparent est ajouté avant validation.",
  },
  {
    q: "Combien coûte une prestation ?",
    a: "Coupe adulte 25 €, coupe + barbe 35 €, coupe enfant 18 €. Le total, durée et éventuel supplément sont affichés avant de confirmer.",
  },
  {
    q: "Puis-je réserver pour plusieurs personnes ?",
    a: "Oui. Une même réservation peut inclure autant d'adultes et d'enfants que vous le souhaitez, chacun avec sa prestation. Le prix et la durée totale sont calculés automatiquement.",
  },
  {
    q: "Comment payer ?",
    a: "Le paiement sur place est disponible dès aujourd'hui. Le paiement en ligne sécurisé arrive prochainement — l'architecture est déjà prête.",
  },
  {
    q: "Puis-je annuler ?",
    a: "Oui, tant que le barber n'est pas en route, vous pouvez annuler depuis votre espace client en un clic.",
  },
];
