/**
 * Réponses HTTP JSON normalisées.
 *
 * Format de succès : { "data": ... }
 * Format d'erreur  : { "error": { "message": string, "code"?: string } }
 *
 * Toutes les réponses portent les en-têtes CORS.
 */
import { corsHeaders } from './cors.ts';

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

/** Réponse de succès. */
export function ok<T>(data: T, status = 200): Response {
  return jsonResponse({ data }, status);
}

/** Réponse d'erreur. */
export function error(message: string, status = 400, code?: string): Response {
  return jsonResponse({ error: { message, code } }, status);
}
