// Identifiants stables des catégories internes (lignes générées par les boutons
// TVA / Récupérer TVA). Non affichées dans la grille de saisie.
export const SYSTEM_CATEGORY = {
  TVA: "sys-tva",
  TVA_RECUPEREE: "sys-tva-recuperee",
} as const;

// Catégories restreintes autorisées pour "Récupérer TVA" (§3.5).
export const RECOVERED_VAT_ALLOWED_NAMES = ["Essence", "Location Camionnette"] as const;

export interface SeedCategory {
  id?: string;
  name: string;
  icon: string;
  type: "SUBTRACTION" | "ADDITION";
  isSystem?: boolean;
}

export const DEFAULT_CATEGORIES: SeedCategory[] = [
  // Soustraction (−)
  { name: "Essence", icon: "fuel", type: "SUBTRACTION" },
  { name: "Location Camionnette", icon: "truck", type: "SUBTRACTION" },
  { name: "Frais de facture / Virement bancaire", icon: "receipt", type: "SUBTRACTION" },
  { name: "Licence", icon: "badge", type: "SUBTRACTION" },
  { name: "Frais Mensuel", icon: "calendar-repeat", type: "SUBTRACTION" },
  { name: "Employé Poche", icon: "wallet", type: "SUBTRACTION" },
  // Addition (+)
  { name: "CASA", icon: "home", type: "ADDITION" },
  { name: "Récupérer Poche", icon: "wallet-in", type: "ADDITION" },
  // Internes (générées par calcul, masquées dans la grille)
  { id: SYSTEM_CATEGORY.TVA, name: "TVA", icon: "percent", type: "SUBTRACTION", isSystem: true },
  {
    id: SYSTEM_CATEGORY.TVA_RECUPEREE,
    name: "TVA récupérée",
    icon: "percent-in",
    type: "ADDITION",
    isSystem: true,
  },
];
