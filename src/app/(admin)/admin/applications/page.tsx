import type { Metadata } from "next";
import { UserPlus, Instagram, Phone, Award } from "lucide-react";
import { requireRole } from "@/server/session";
import { getBarberApplications } from "@/server/admin";
import { PageHeader, EmptyState } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarberModeration } from "@/components/admin/barber-moderation";
import { barberLevelLabel } from "@/lib/barber";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Demandes de création de compte" };
export const dynamic = "force-dynamic";

export default async function AdminApplicationsPage() {
  await requireRole(["ADMIN"]);
  const applications = await getBarberApplications();

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader
        title="Demandes de création de compte"
        subtitle="Dossiers barber en attente de validation."
      />

      {applications.length === 0 ? (
        <EmptyState
          icon={UserPlus}
          title="Aucune demande en attente"
          description="Les nouvelles candidatures de barbers apparaîtront ici."
        />
      ) : (
        <div className="space-y-4">
          {applications.map((a) => (
            <Card key={a.id} className="space-y-4 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    {a.user.firstName} {a.user.lastName}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {a.user.email} · déposé le {formatDate(a.createdAt)}
                  </p>
                </div>
                <Badge className="gap-1">
                  <Award className="size-3" />
                  {barberLevelLabel(a.level)}
                </Badge>
              </div>

              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="size-4 text-gold" />
                  {a.user.phone ?? "—"}
                </span>
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Instagram className="size-4 text-gold" />
                  {a.instagram ? `@${a.instagram}` : "—"}
                </span>
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Award className="size-4 text-gold" />
                  {a.yearsExperience} an(s) d&apos;expérience
                </span>
              </div>

              {a.bio && (
                <p className="rounded-lg bg-secondary/50 px-3 py-2 text-sm text-muted-foreground">
                  {a.bio}
                </p>
              )}

              <BarberModeration barberId={a.id} actions={["APPROVE", "REFUSE"]} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
