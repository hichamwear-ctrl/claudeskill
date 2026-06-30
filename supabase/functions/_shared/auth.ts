/**
 * Helpers d'authentification pour les Edge Functions.
 *
 * Le runtime vérifie déjà la signature du JWT (verify_jwt). Ici on en extrait
 * l'utilisateur et son rôle applicatif (claim `user_role` injecté par le Custom
 * Access Token Hook, §5.2) afin d'autoriser finement chaque opération.
 */
import type { SupabaseClient } from '@supabase/supabase-js';
import { Forbidden, Unauthorized } from './errors.ts';

export type UserRole = 'client' | 'operator' | 'admin';

export interface AuthContext {
  userId: string;
  role: UserRole;
}

/** Décode (sans vérifier la signature) la charge utile du JWT de la requête. */
function decodeClaims(req: Request): Record<string, unknown> | null {
  const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '');
  const payload = token?.split('.')[1];
  if (!payload) return null;
  try {
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Exige un utilisateur authentifié. Valide le token via Supabase puis lit le
 * rôle depuis le claim `user_role` (défaut 'client').
 */
export async function requireUser(client: SupabaseClient, req: Request): Promise<AuthContext> {
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) {
    throw Unauthorized();
  }
  const claims = decodeClaims(req);
  const role = (claims?.['user_role'] as UserRole) ?? 'client';
  return { userId: data.user.id, role };
}

/** Exige que l'utilisateur possède l'un des rôles autorisés. */
export function requireRole(ctx: AuthContext, ...roles: UserRole[]): void {
  if (!roles.includes(ctx.role)) {
    throw Forbidden(`Rôle requis: ${roles.join(' ou ')}`);
  }
}
