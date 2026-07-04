import {
  CalendarCheck,
  CalendarRange,
  Wallet,
  Users,
  Scissors,
  Zap,
  Clock,
} from "lucide-react";
import { requireRole } from "@/lib/session";
import { getAdminStats } from "@/lib/admin";
import { PageHeader, StatCard } from "@/components/dashboard/common";
import { WeeklyChart } from "@/components/dashboard/bar-chart";
import { AutoRefresh } from "@/components/dashboard/auto-refresh";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function AdminDashboardPage() {
  await requireRole(["ADMIN"]);
  const stats = await getAdminStats();

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <AutoRefresh intervalMs={20_000} />
      <PageHeader
        title="Vue d'ensemble"
        subtitle="Pilotez toute la plateforme Barber Home."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Réservations aujourd'hui" value={stats.todayCount} icon={CalendarCheck} accent />
        <StatCard label="Cette semaine" value={stats.weekCount} icon={CalendarRange} />
        <StatCard label="Chiffre d'affaires" value={formatCurrency(stats.revenue)} icon={Wallet} />
        <StatCard label="En attente" value={stats.pending} icon={Clock} hint="Demandes à traiter" />
        <StatCard label="Clients" value={stats.clients} icon={Users} />
        <StatCard label="Barbers" value={stats.barbers} icon={Scissors} />
        <StatCard label="Barbers dispo" value={stats.availableBarbers} icon={Zap} />
        <StatCard
          label="Taux dispo"
          value={`${stats.barbers ? Math.round((stats.availableBarbers / stats.barbers) * 100) : 0}%`}
          icon={Zap}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Activité des 7 derniers jours</CardTitle>
        </CardHeader>
        <CardContent>
          <WeeklyChart data={stats.series} />
        </CardContent>
      </Card>
    </div>
  );
}
