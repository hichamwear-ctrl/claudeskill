import Link from "next/link";
import { CalendarPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { greeting } from "@/lib/utils";

/**
 * Premium welcome banner (Phase 4 UI). A barbershop ambiance visual behind the
 * greeting — same information as before, nicer arrangement, less "raw data".
 */
export function WelcomeBanner({ firstName }: { firstName: string }) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-border bg-cover bg-center premium-shadow"
      style={{ backgroundImage: "url('/images/barbershop-scene.svg')" }}
    >
      <div className="bg-gradient-to-r from-background via-background/90 to-background/30 p-6 sm:p-8">
        <p className="text-sm font-medium text-gold">{greeting()}</p>
        <h1 className="mt-1 font-display text-2xl font-bold tracking-tight sm:text-3xl">
          {firstName} 👋
        </h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Prêt pour une coupe à domicile ?
        </p>
        <Button asChild className="mt-4">
          <Link href="/client/book">
            <CalendarPlus className="size-4" />
            Nouvelle réservation
          </Link>
        </Button>
      </div>
    </div>
  );
}
