import type { Metadata } from "next";
import { Phone, MessageSquare, Award } from "lucide-react";
import { requireRole } from "@/server/session";
import { getBarbersForModeration } from "@/server/admin";
import { PageHeader } from "@/components/dashboard/common";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { BarberModeration } from "@/components/admin/barber-moderation";
import { AdminNoteForm } from "@/components/admin/note-form";
import { barberLevelLabel } from "@/lib/barber";
import { formatDate, getInitials } from "@/lib/utils";

export const metadata: Metadata = { title: "Barbers" };
export const dynamic = "force-dynamic";

export default async function AdminBarbersPage() {
  await requireRole(["ADMIN"]);
  const barbers = await getBarbersForModeration();

  return (
    <div className="space-y-8 p-5 sm:p-8">
      <PageHeader title="Barbers" subtitle={`${barbers.length} barber(s) actif(s).`} />
      <div className="grid gap-4 lg:grid-cols-2">
        {barbers.map((b) => {
          const banned = b.bannedAt != null;
          const suspended = b.suspendedAt != null;
          return (
            <Card key={b.id} className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar className="size-11 rounded-xl">
                    {b.user.image && <AvatarImage src={b.user.image} alt="" />}
                    <AvatarFallback className="rounded-xl">
                      {getInitials(b.user.firstName, b.user.lastName)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium">
                      {b.user.firstName} {b.user.lastName}
                    </p>
                    <p className="text-xs text-muted-foreground">{b.user.email}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge className="gap-1">
                    <Award className="size-3" />
                    {barberLevelLabel(b.level)}
                  </Badge>
                  {banned && (
                    <Badge className="border-rose-400/30 bg-rose-400/10 text-rose-400">
                      Banni
                    </Badge>
                  )}
                  {suspended && !banned && (
                    <Badge className="border-amber-400/30 bg-amber-400/10 text-amber-400">
                      Suspendu
                    </Badge>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center">
                <Metric label="Note" value={b.rating.toFixed(1)} />
                <Metric label="Avis" value={b._count.reviews} />
                <Metric label="Courses" value={b._count.reservations} />
              </div>

              {/* Direct contact (spec: appeler / discuter avec un barber) */}
              <div className="flex flex-wrap gap-2">
                {b.user.phone && (
                  <Button variant="secondary" size="sm" asChild>
                    <a href={`tel:${b.user.phone}`}>
                      <Phone className="size-4" /> Appeler
                    </a>
                  </Button>
                )}
                <Button variant="secondary" size="sm" asChild>
                  <a href={`mailto:${b.user.email}`}>
                    <MessageSquare className="size-4" /> Contacter
                  </a>
                </Button>
              </div>

              <BarberModeration
                barberId={b.id}
                actions={[
                  banned ? "UNBAN" : "BAN",
                  suspended ? "UNSUSPEND" : "SUSPEND",
                  "DELETE",
                ]}
              />

              <div className="space-y-2 border-t border-border pt-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Notes internes
                </p>
                {b.adminNotes.length > 0 && (
                  <ul className="space-y-1 text-sm">
                    {b.adminNotes.map((n) => (
                      <li key={n.id} className="text-muted-foreground">
                        <span className="text-foreground">{n.body}</span>
                        <span className="ml-1 text-[11px]">
                          — {n.author.firstName}, {formatDate(n.createdAt)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <AdminNoteForm barberId={b.id} />
              </div>
            </Card>
          );
        })}
        {barbers.length === 0 && (
          <p className="text-sm text-muted-foreground">Aucun barber actif.</p>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-secondary/50 py-2">
      <p className="text-sm font-semibold">{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}
