import type { Metadata } from "next";
import { ShieldCheck, TriangleAlert, LifeBuoy } from "lucide-react";
import { requireRole } from "@/server/session";
import { getOpenReports } from "@/server/admin";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ResolveReportButton } from "@/components/admin/resolve-report";
import { formatDateTime } from "@/lib/utils";

export const metadata: Metadata = { title: "Signalements" };
export const dynamic = "force-dynamic";

export default async function AdminReportsPage() {
  await requireRole(["ADMIN"]);
  const reports = await getOpenReports();

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Signalements & demandes d'aide"
        subtitle={`${reports.length} à traiter.`}
      />

      {reports.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="Rien à signaler"
          description="Les signalements et demandes d'aide des clients apparaîtront ici."
        />
      ) : (
        <div className="space-y-4">
          {reports.map((r) => (
            <Card key={r.id} className="space-y-3 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  {r.type === "PROBLEM" ? (
                    <Badge className="gap-1 border-rose-400/30 bg-rose-400/10 text-rose-400">
                      <TriangleAlert className="size-3" /> Problème
                    </Badge>
                  ) : (
                    <Badge className="gap-1 border-sky-400/30 bg-sky-400/10 text-sky-400">
                      <LifeBuoy className="size-3" /> Aide
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(r.createdAt)}
                  </span>
                </div>
                <ResolveReportButton reportId={r.id} />
              </div>

              <p className="text-sm">{r.message}</p>

              <p className="text-xs text-muted-foreground">
                Par {r.reporter.firstName} {r.reporter.lastName}
                {r.barber &&
                  ` · barber : ${r.barber.user.firstName} ${r.barber.user.lastName}`}
                {r.reservation &&
                  ` · commande ${r.reservation.reference.slice(0, 8).toUpperCase()}`}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
