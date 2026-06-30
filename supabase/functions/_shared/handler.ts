/**
 * Wrapper standard pour toute Edge Function.
 *
 * Centralise : préflight CORS, requestId de corrélation, journalisation
 * d'entrée/sortie, et conversion des erreurs (HttpError -> réponse propre,
 * erreur inattendue -> 500 générique sans fuite de détail).
 *
 * Usage :
 *   import { serve } from '../_shared/handler.ts';
 *   import { ok } from '../_shared/http.ts';
 *   serve('ma-fonction', async (req, { log }) => { ... return ok(data); });
 */
import { handlePreflight } from './cors.ts';
import { error as errorResponse } from './http.ts';
import { HttpError } from './errors.ts';
import { createLogger, type Logger } from './logger.ts';

export interface RequestContext {
  requestId: string;
  log: Logger;
}

export type Handler = (req: Request, ctx: RequestContext) => Promise<Response> | Response;

export function serve(name: string, handler: Handler): void {
  Deno.serve(async (req: Request) => {
    const preflight = handlePreflight(req);
    if (preflight) return preflight;

    const requestId = req.headers.get('x-request-id') ?? crypto.randomUUID();
    const log = createLogger(name, requestId);
    const startedAt = Date.now();

    try {
      const response = await handler(req, { requestId, log });
      log.info('request.done', { status: response.status, ms: Date.now() - startedAt });
      return response;
    } catch (err) {
      if (err instanceof HttpError) {
        log.warn('request.error', { status: err.status, code: err.code, message: err.message });
        return errorResponse(err.message, err.status, err.code);
      }
      log.error('request.unhandled', {
        ms: Date.now() - startedAt,
        message: err instanceof Error ? err.message : String(err),
      });
      return errorResponse('Erreur interne', 500, 'internal_error');
    }
  });
}
