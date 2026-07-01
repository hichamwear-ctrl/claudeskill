/**
 * Erreur HTTP typée, convertie en réponse JSON par le wrapper `serve()`.
 * Permet à toute fonction de signaler proprement un statut + un code stable.
 */
export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'HttpError';
  }
}

/** Raccourcis pour les cas fréquents. */
export const Unauthorized = (message = 'Non authentifié') =>
  new HttpError(401, message, 'unauthenticated');

export const Forbidden = (message = 'Accès refusé') => new HttpError(403, message, 'forbidden');

export const BadRequest = (message = 'Requête invalide', code = 'bad_request') =>
  new HttpError(400, message, code);

export const NotFound = (message = 'Introuvable', code = 'not_found') =>
  new HttpError(404, message, code);

export const Conflict = (message = 'Conflit', code = 'conflict') =>
  new HttpError(409, message, code);

/** 422 — requête bien formée mais sémantiquement incomplète (ex. dossier partiel). */
export const Unprocessable = (message = 'Traitement impossible', code = 'unprocessable') =>
  new HttpError(422, message, code);
