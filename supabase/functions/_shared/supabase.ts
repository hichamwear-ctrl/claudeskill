/**
 * Fabriques de clients Supabase pour les Edge Functions.
 *
 * - createUserClient : agit AU NOM de l'utilisateur appelant (transmet son JWT)
 *   -> soumis à la RLS. À utiliser par défaut.
 * - createAdminClient : utilise la clé service_role -> CONTOURNE la RLS.
 *   À réserver aux opérations serveur contrôlées (paiement, push, attribution...).
 *   Ne JAMAIS exposer la clé service_role côté client (§4.5).
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL } from './env.ts';

/** Client soumis à la RLS, authentifié avec le JWT de la requête entrante. */
export function createUserClient(req: Request): SupabaseClient {
  const authorization = req.headers.get('Authorization') ?? '';
  return createClient(SUPABASE_URL(), SUPABASE_ANON_KEY(), {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/** Client privilégié (service_role) — contourne la RLS. Usage serveur uniquement. */
export function createAdminClient(): SupabaseClient {
  return createClient(SUPABASE_URL(), SUPABASE_SERVICE_ROLE_KEY(), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
