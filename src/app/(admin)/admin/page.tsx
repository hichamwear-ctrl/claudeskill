import Link from "next/link";
import {
  CalendarCheck,
  CalendarRange,
  Wallet,
  Users,
  Scissors,
  Zap,
  Clock,
  UserPlus,
  ShieldAlert,
} from "lucide-react";
import { requireRole } from "@/server/session";
import { getAdminStats } from "@/server/admin";
import { PageHeader, StatCard } from "@/components/dashboard/common";
import { WeeklyChart } from "@/components/dashboard/bar-chart";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function AdminDashboardPage() {
  await requireRole(["ADMIN"]);
  const stats = await getAdminStats();

  return (
    <div className="space-y-8 p-5 sm:p-8">
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

      {(stats.pendingApplications > 0 || stats.openReports > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {stats.pendingApplications > 0 && (
            <Link href="/admin/applications">
              <Card className="flex items-center gap-3 p-4 transition-colors hover:border-gold/40">
                <UserPlus className="size-5 text-gold" />
                <p className="text-sm">
                  <span className="font-semibold">{stats.pendingApplications}</span>{" "}
                  demande(s) de compte barber à valider
                </p>
              </Card>
            </Link>
          )}
          {stats.openReports > 0 && (
            <Link href="/admin/reports">
              <Card className="flex items-center gap-3 p-4 transition-colors hover:border-gold/40">
                <ShieldAlert className="size-5 text-rose-400" />
                <p className="text-sm">
                  <span className="font-semibold">{stats.openReports}</span>{" "}
                  signalement(s) à traiter
                </p>
              </Card>
            </Link>
          )}
        </div>
      )}

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
