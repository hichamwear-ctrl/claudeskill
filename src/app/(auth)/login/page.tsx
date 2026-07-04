import type { Metadata } from "next";
import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Connexion" };

export default function LoginPage() {
  return (
    <div>
      <div className="mb-6 text-center">
        <h1 className="font-display text-2xl font-bold">Bon retour</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Connectez-vous pour accéder à votre espace.
        </p>
      </div>
      <LoginForm />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-medium text-gold hover:underline">
          Créer un compte
        </Link>
      </p>
    </div>
  );
}
