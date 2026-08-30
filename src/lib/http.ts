import { NextResponse } from "next/server";
import { ZodError } from "zod";
import { auth } from "./auth";

/** Erreur applicative portant un code HTTP (jamais silencieuse). */
export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Authentification requise (admin OU lecteur). */
export async function requireAuth() {
  const session = await auth();
  if (!session?.user) throw new HttpError(401, "Non authentifié");
  return session;
}

/**
 * Écriture réservée à l'admin — vérifiée CÔTÉ SERVEUR sur chaque route.
 * Le rôle READER n'atteint jamais une route de création/modification/suppression.
 */
export async function requireAdmin() {
  const session = await requireAuth();
  if (session.user.role !== "ADMIN") {
    throw new HttpError(403, "Accès refusé");
  }
  return session;
}

/** Enveloppe uniforme : transforme les erreurs en réponses JSON propres. */
export async function handle(fn: () => Promise<NextResponse | Response>) {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof HttpError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    if (err instanceof ZodError) {
      return NextResponse.json(
        { error: "Données invalides", details: err.flatten() },
        { status: 422 },
      );
    }
    // Aucune fuite d'implémentation en production.
    return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
  }
}

export function json(data: unknown, status = 200) {
  return NextResponse.json(data, { status });
}
