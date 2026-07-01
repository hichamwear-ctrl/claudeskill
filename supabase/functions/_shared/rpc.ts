/**
 * Traduction des erreurs des RPC PostgreSQL (SQLSTATE) en `HttpError`.
 *
 * Les fonctions SECURITY DEFINER (transition_mission, claim_review…) signalent
 * leurs refus via `raise exception ... using errcode = <condition>`. supabase-js
 * renvoie alors `{ code: SQLSTATE, message }`. On mappe vers des statuts HTTP
 * stables sans exposer de détail interne superflu.
 */
import { HttpError } from './errors.ts';
import type { PostgrestError } from '@supabase/supabase-js';

const STATUS_BY_SQLSTATE: Record<string, number> = {
  '02000': 404, // no_data_found
  '23514': 409, // check_violation (transition/étape interdite, hors file…)
  '23505': 409, // unique_violation (déjà claimé)
  '42501': 403, // insufficient_privilege (rôle / claim / propriété)
  '23502': 422, // not_null_violation (motif/prix requis)
};

/** Convertit une erreur RPC en HttpError (statut mappé, message serveur repris). */
export function rpcError(error: PostgrestError): HttpError {
  const status = STATUS_BY_SQLSTATE[error.code] ?? 400;
  return new HttpError(status, error.message, `pg_${error.code}`);
}
