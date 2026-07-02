import { describe, expect, it } from '@jest/globals';

import { toUxError } from '../errorCatalog';
import { AppError, normalizeErrorCode } from '../errors';

describe('normalizeErrorCode', () => {
  it('conserve un code serveur connu', () => {
    expect(normalizeErrorCode('payment_locked', 409)).toBe('payment_locked');
  });

  it('déduit le code depuis le statut HTTP si le code est inconnu', () => {
    expect(normalizeErrorCode(undefined, 401)).toBe('unauthenticated');
    expect(normalizeErrorCode('weird', 403)).toBe('forbidden');
    expect(normalizeErrorCode(undefined, 0)).toBe('network_error');
    expect(normalizeErrorCode(undefined, 500)).toBe('internal_error');
  });
});

describe('toUxError', () => {
  it('mappe un AppError vers une présentation UX (ERR_*)', () => {
    const ux = toUxError(new AppError('payment_locked', 'x', 409));
    expect(ux.uxCode).toBe('ERR_PAY_LOCKED');
    expect(ux.action).toBe('wait');
  });

  it('retombe sur une erreur générique pour une valeur inconnue', () => {
    expect(toUxError(new Error('boom')).uxCode).toBe('ERR_SERVER');
  });
});
