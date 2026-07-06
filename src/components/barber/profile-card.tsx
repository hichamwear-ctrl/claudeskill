import { Star, Award, Instagram, Ghost } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { barberLevelLabel, starString } from "@/lib/barber";
import { getInitials, formatDate } from "@/lib/utils";
import type { BarberPublicProfile } from "@/server/barber";

/** Full public barber profile: identity, seniority, portfolio, bio, reviews. */
export function BarberProfileCard({ profile }: { profile: BarberPublicProfile }) {
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Avatar className="size-16">
          {profile.image && <AvatarImage src={profile.image} alt="" />}
          <AvatarFallback className="text-lg">
            {getInitials(profile.firstName, profile.lastName)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-xl font-bold">
            {profile.firstName} {profile.lastName}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <Badge className="gap-1">
              <Award className="size-3" />
              {barberLevelLabel(profile.level)}
            </Badge>
            <span className="text-muted-foreground">
              {profile.yearsExperience} an(s) d&apos;expérience
            </span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="flex items-center gap-1 text-gold">
              <Star className="size-4 fill-current" />
              {profile.rating.toFixed(1)}
            </span>
            <span className="text-muted-foreground">
              ({profile.reviewCount} avis)
            </span>
          </div>
          {(profile.instagram || profile.snapchat) && (
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
              {profile.instagram && (
                <span className="flex items-center gap-1">
                  <Instagram className="size-3" />@{profile.instagram}
                </span>
              )}
              {profile.snapchat && (
                <span className="flex items-center gap-1">
                  <Ghost className="size-3" />
                  {profile.snapchat}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {profile.bio && (
        <p className="text-sm leading-relaxed text-muted-foreground">{profile.bio}</p>
      )}

      {profile.photos.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold">Réalisations</p>
          <div className="grid grid-cols-3 gap-2">
            {profile.photos.map((p) => (
              <div
                key={p.id}
                className="relative aspect-square overflow-hidden rounded-xl bg-secondary"
              >
                {/* Portfolio images are user-supplied URLs / data URIs. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={p.url}
                  alt={p.caption ?? "Réalisation"}
                  className="size-full object-cover"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {profile.reviews.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold">Avis clients</p>
          <div className="space-y-3">
            {profile.reviews.map((r) => (
              <div key={r.id} className="rounded-xl border border-border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{r.author.firstName}</span>
                  <span className="text-gold">{starString(r.rating)}</span>
                </div>
                {r.comment && (
                  <p className="mt-1 italic text-muted-foreground">
                    &ldquo;{r.comment}&rdquo;
                  </p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(r.createdAt)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
