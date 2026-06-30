/**
 * Gestion CORS centralisée.
 *
 * L'origine autorisée est configurable via la variable d'environnement
 * CORS_ALLOW_ORIGIN (défaut '*'). À restreindre aux domaines de l'app en prod.
 */
import { optionalEnv } from './env.ts';

export const corsHeaders: Record<string, string> = {
  'Access-Control-Allow-Origin': optionalEnv('CORS_ALLOW_ORIGIN', '*'),
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type, x-request-id',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
};

/**
 * Répond au préflight CORS (OPTIONS). Retourne null si la requête n'est pas un
 * préflight, pour laisser le handler poursuivre.
 */
export function handlePreflight(req: Request): Response | null {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }
  return null;
}
