import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";

export default function NotFound() {
  return (
    <div className="noise-bg flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <Logo />
      <div>
        <p className="font-display text-7xl font-bold text-gold-gradient">404</p>
        <p className="mt-2 text-lg font-medium">Page introuvable</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Cette page n&apos;existe pas ou a été déplacée.
        </p>
      </div>
      <Button asChild>
        <Link href="/">Retour à l&apos;accueil</Link>
      </Button>
    </div>
  );
}
