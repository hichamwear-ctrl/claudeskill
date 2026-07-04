import { requireRole } from "@/server/session";
import { DashboardShell, type NavItem } from "@/components/dashboard/shell";

const NAV: NavItem[] = [
  { href: "/client", label: "Tableau de bord", icon: "LayoutDashboard" },
  { href: "/client/book", label: "Nouvelle réservation", icon: "CalendarPlus" },
  { href: "/client/history", label: "Historique & factures", icon: "ReceiptText" },
  { href: "/client/addresses", label: "Mes adresses", icon: "MapPin" },
  { href: "/client/profile", label: "Profil", icon: "User" },
];

export default async function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole(["CLIENT", "ADMIN"]);
  return (
    <DashboardShell nav={NAV} user={session.user} roleLabel="Client">
      {children}
    </DashboardShell>
  );
}
