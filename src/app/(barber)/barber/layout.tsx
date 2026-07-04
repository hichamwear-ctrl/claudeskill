import {
  LayoutDashboard,
  CalendarClock,
  History,
  Wallet,
  User,
} from "lucide-react";
import { requireRole } from "@/lib/session";
import { DashboardShell, type NavItem } from "@/components/dashboard/shell";

const NAV: NavItem[] = [
  { href: "/barber", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/barber/planning", label: "Planning", icon: CalendarClock },
  { href: "/barber/history", label: "Historique", icon: History },
  { href: "/barber/earnings", label: "Revenus", icon: Wallet },
  { href: "/client/profile", label: "Profil", icon: User },
];

export default async function BarberLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole(["BARBER", "ADMIN"]);
  return (
    <DashboardShell nav={NAV} user={session.user} roleLabel="Barber">
      {children}
    </DashboardShell>
  );
}
