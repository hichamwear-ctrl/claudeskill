import type { PostgrestError } from '@supabase/supabase-js';

/**
 * Codes d'erreur stables partagés avec le backend (API_SPEC §2 / UX_SPEC §8).
 * `network_error` est ajouté côté client (échec de transport, hors serveur).
 */
export type ErrorCode =
  | 'network_error'
  | 'unauthenticated'
  | 'forbidden'
  | 'bad_request'
  | 'not_found'
  | 'conflict'
  | 'payment_locked'
  | 'price_expired'
  | 'zone_uncovered'
  | 'out_of_hours'
  | 'validation_failed'
  | 'rate_limited'
  | 'internal_error';

/** Erreur applicative normalisée : seule forme d'erreur qui circule dans l'app. */
export class AppError extends Error {
  readonly code: ErrorCode;
  readonly httpStatus: number;

  constructor(code: ErrorCode, message: string, httpStatus: number) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.httpStatus = httpStatus;
  }
}

export function isAppError(value: unknown): value is AppError {
  return value instanceof AppError;
}

const KNOWN_CODES: ReadonlySet<string> = new Set<ErrorCode>([
  'network_error',
  'unauthenticated',
  'forbidden',
  'bad_request',
  'not_found',
  'conflict',
  'payment_locked',
  'price_expired',
  'zone_uncovered',
  'out_of_hours',
  'validation_failed',
  'rate_limited',
  'internal_error',
]);

/** Déduit un `ErrorCode` sûr depuis un code serveur libre + un statut HTTP. */
export function normalizeErrorCode(rawCode: string | undefined, httpStatus: number): ErrorCode {
  if (rawCode && KNOWN_CODES.has(rawCode)) return rawCode as ErrorCode;
  switch (httpStatus) {
    case 401:
      return 'unauthenticated';
    case 403:
      return 'forbidden';
    case 404:
      return 'not_found';
    case 409:
      return 'conflict';
    case 422:
      return 'validation_failed';
    case 429:
      return 'rate_limited';
    case 0:
      return 'network_error';
    default:
      return httpStatus >= 500 ? 'internal_error' : 'bad_request';
  }
}

/** SQLSTATE (Postgres) → (ErrorCode, statut HTTP indicatif). */
const SQLSTATE_MAP: Record<string, { code: ErrorCode; httpStatus: number }> = {
  '42501': { code: 'forbidden', httpStatus: 403 }, // insufficient_privilege
  P0001: { code: 'validation_failed', httpStatus: 422 }, // raise exception générique
  P0002: { code: 'not_found', httpStatus: 404 }, // no_data_found
  '23505': { code: 'conflict', httpStatus: 409 }, // unique_violation
  '23503': { code: 'conflict', httpStatus: 409 }, // foreign_key_violation
  '23514': { code: 'validation_failed', httpStatus: 422 }, // check_violation
  '22023': { code: 'validation_failed', httpStatus: 422 }, // invalid_parameter_value
  PGRST: { code: 'not_found', httpStatus: 404 }, // erreurs PostgREST (préfixe)
};

/**
 * Convertit une erreur PostgREST/RPC en `AppError`.
 * Les RPC `SECURITY DEFINER` signalent leurs erreurs métier via SQLSTATE ;
 * on les traduit vers le catalogue stable partagé avec les Edge Functions.
 */
export function mapPostgrestError(error: PostgrestError): AppError {
  const raw = error.code ?? '';
  const match = SQLSTATE_MAP[raw] ?? (raw.startsWith('PGRST') ? SQLSTATE_MAP.PGRST : undefined);
  if (match) return new AppError(match.code, error.message || 'Erreur base de données', match.httpStatus);
  return new AppError('bad_request', error.message || 'Erreur base de données', 400);
}
