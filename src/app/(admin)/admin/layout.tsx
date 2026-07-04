import {
  LayoutDashboard,
  CalendarRange,
  Scissors,
  Users,
  Star,
  Tag,
} from "lucide-react";
import { requireRole } from "@/lib/session";
import { DashboardShell, type NavItem } from "@/components/dashboard/shell";

const NAV: NavItem[] = [
  { href: "/admin", label: "Vue d'ensemble", icon: LayoutDashboard },
  { href: "/admin/reservations", label: "Réservations", icon: CalendarRange },
  { href: "/admin/barbers", label: "Barbers", icon: Scissors },
  { href: "/admin/clients", label: "Clients", icon: Users },
  { href: "/admin/reviews", label: "Avis", icon: Star },
  { href: "/admin/promos", label: "Promotions", icon: Tag },
];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole(["ADMIN"]);
  return (
    <DashboardShell nav={NAV} user={session.user} roleLabel="Administrateur">
      {children}
    </DashboardShell>
  );
}
