import { Logo } from "@/components/logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 py-12">
      <div className="container flex flex-col items-center justify-between gap-6 md:flex-row">
        <div className="flex flex-col items-center gap-3 md:items-start">
          <Logo />
          <p className="text-sm text-muted-foreground">
            Le barber premium à domicile — Bruxelles.
          </p>
        </div>
        <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground md:items-end">
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground">
              Conditions
            </a>
            <a href="#" className="hover:text-foreground">
              Confidentialité
            </a>
            <a href="#" className="hover:text-foreground">
              Contact
            </a>
          </div>
          <p>© {new Date().getFullYear()} Barber Home. Tous droits réservés.</p>
        </div>
      </div>
    </footer>
  );
}
