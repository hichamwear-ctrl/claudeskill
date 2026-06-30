/**
 * Fonction d'exemple `health` — vérifie que le runtime Edge Functions répond.
 *
 * Publique (verify_jwt = false, voir config.toml) afin de servir de sonde de
 * disponibilité. Ne contient AUCUNE logique métier ni accès aux données.
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';

serve('health', () =>
  ok({
    status: 'ok',
    service: 'edge-functions',
    time: new Date().toISOString(),
  }));
