import type { Metadata } from "next";
import Link from "next/link";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = { title: "Créer un compte" };

export default function RegisterPage() {
  return (
    <div>
      <div className="mb-6 text-center">
        <h1 className="font-display text-2xl font-bold">Créer un compte</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Rejoignez Barber Home en quelques secondes.
        </p>
      </div>
      <RegisterForm />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Déjà inscrit ?{" "}
        <Link href="/login" className="font-medium text-gold hover:underline">
          Se connecter
        </Link>
      </p>
    </div>
  );
}
