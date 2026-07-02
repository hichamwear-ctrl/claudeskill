import type { ErrorCode } from './errors';
import { isAppError } from './errors';

/**
 * Mappe un `ErrorCode` vers une présentation UX (UX_SPEC §8) : clé `ERR_*`,
 * message rassurant (FR) et action suggérée. Aucun code brut n'est montré.
 * Les messages peuvent être surchargés via i18n (clé `errors.<ERR_*>`).
 */
export interface UxError {
  uxCode: string;
  message: string;
  action: 'retry' | 'settings' | 'wait' | 'new_request' | 'reauth' | 'none';
}

const CATALOG: Record<ErrorCode, UxError> = {
  network_error: { uxCode: 'ERR_NETWORK', message: 'Connexion perdue.', action: 'retry' },
  unauthenticated: { uxCode: 'ERR_SESSION', message: 'Reconnectez-vous.', action: 'reauth' },
  forbidden: { uxCode: 'ERR_FORBIDDEN', message: 'Action non autorisée.', action: 'none' },
  bad_request: { uxCode: 'ERR_BAD_REQUEST', message: 'Requête invalide.', action: 'retry' },
  not_found: { uxCode: 'ERR_NOT_FOUND', message: 'Élément introuvable.', action: 'none' },
  conflict: { uxCode: 'ERR_CONFLICT', message: 'Action déjà effectuée ou état modifié.', action: 'none' },
  payment_locked: {
    uxCode: 'ERR_PAY_LOCKED',
    message: 'Le paiement sera possible après validation de votre demande.',
    action: 'wait',
  },
  price_expired: { uxCode: 'ERR_PRICE_EXPIRED', message: 'L’offre a expiré.', action: 'new_request' },
  zone_uncovered: {
    uxCode: 'ERR_ZONE_UNCOVERED',
    message: 'Pas encore disponible chez vous.',
    action: 'none',
  },
  out_of_hours: { uxCode: 'ERR_OUT_OF_HOURS', message: 'Service fermé pour le moment.', action: 'wait' },
  validation_failed: {
    uxCode: 'ERR_VALIDATION',
    message: 'Certaines informations sont incomplètes.',
    action: 'retry',
  },
  rate_limited: { uxCode: 'ERR_RATE_LIMIT', message: 'Trop d’essais, réessayez plus tard.', action: 'wait' },
  internal_error: { uxCode: 'ERR_SERVER', message: 'Une erreur est survenue.', action: 'retry' },
};

const FALLBACK: UxError = CATALOG.internal_error;

/** Traduit n'importe quelle erreur en présentation UX exploitable. */
export function toUxError(error: unknown): UxError {
  if (isAppError(error)) return CATALOG[error.code] ?? FALLBACK;
  return FALLBACK;
}
