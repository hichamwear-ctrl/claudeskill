// Jeu d'icônes par emoji (zéro dépendance, rendu universel sur mobile).
const ICONS: Record<string, string> = {
  fuel: "⛽",
  truck: "🚚",
  receipt: "🧾",
  badge: "🪪",
  "calendar-repeat": "🗓️",
  wallet: "👛",
  home: "🏠",
  "wallet-in": "💰",
  percent: "📉",
  "percent-in": "📈",
  tag: "🏷️",
  card: "💳",
  tool: "🔧",
  cart: "🛒",
  box: "📦",
  phone: "📱",
  bolt: "⚡",
  star: "⭐",
};

export function Icon({ name }: { name: string }) {
  return <span aria-hidden>{ICONS[name] ?? "🏷️"}</span>;
}

// Liste proposée à l'admin pour créer une catégorie (§3.3).
export const ICON_CHOICES = Object.keys(ICONS);
