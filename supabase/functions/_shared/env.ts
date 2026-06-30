/**
 * Accès centralisé et validé aux variables d'environnement.
 *
 * Les variables SUPABASE_* sont injectées automatiquement dans le runtime des
 * Edge Functions. Les secrets (Stripe, Twilio, Expo...) seront ajoutés via
 * `supabase secrets set` lors des étapes correspondantes.
 */

/** Récupère une variable obligatoire ou lève une erreur explicite. */
export function requireEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) {
    throw new Error(`Variable d'environnement manquante: ${name}`);
  }
  return value;
}

/** Récupère une variable optionnelle avec valeur par défaut. */
export function optionalEnv(name: string, fallback = ''): string {
  return Deno.env.get(name) ?? fallback;
}

/** Variables fournies d'office par le runtime Supabase Edge Functions. */
export const SUPABASE_URL = (): string => requireEnv('SUPABASE_URL');
export const SUPABASE_ANON_KEY = (): string => requireEnv('SUPABASE_ANON_KEY');
export const SUPABASE_SERVICE_ROLE_KEY = (): string => requireEnv('SUPABASE_SERVICE_ROLE_KEY');
