import Link from "next/link";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { auth } from "@/server/auth";
import { dashboardPath } from "@/server/session";

export async function SiteHeader() {
  const session = await auth();

  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div className="container flex h-16 items-center justify-between">
        <div className="glass flex h-12 w-full items-center justify-between rounded-full px-4 pl-5 premium-shadow">
          <Logo />
          <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
            <a href="#services" className="transition-colors hover:text-foreground">
              Services
            </a>
            <a href="#how" className="transition-colors hover:text-foreground">
              Comment ça marche
            </a>
            <a href="#zone" className="transition-colors hover:text-foreground">
              Zone
            </a>
          </nav>
          <div className="flex items-center gap-2">
            {session?.user ? (
              <Button size="sm" asChild>
                <Link href={dashboardPath(session.user.role)}>Mon espace</Link>
              </Button>
            ) : (
              <>
                <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
                  <Link href="/login">Connexion</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/register">Réserver</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
