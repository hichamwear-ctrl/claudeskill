/**
 * Edge Function `send-push` — TRANSPORT des notifications (M8).
 * Réf. API_SPEC §4.9, NOTIFICATIONS.md.
 *
 * Interne : déclenchée par Database Webhook (service_role). Contient ZÉRO logique
 * métier : toute la résolution data-driven (triggers → templates → content_strings
 * → notifications, idempotence, silence nocturne, min_interval) est faite par la
 * RPC `dispatch_notifications`. Ici on ne fait que :
 *   1. appeler la RPC (qui écrit les notifications, idempotentes) ;
 *   2. pousser via le transport (mock Expo) les notifications à envoyer.
 *
 * Auth : pas de JWT utilisateur (webhook) ; secret partagé optionnel
 * (`NOTIFY_WEBHOOK_SECRET`) pour verrouiller l'appel.
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest, Forbidden } from '../_shared/errors.ts';
import { rpcError } from '../_shared/rpc.ts';
import { createAdminClient } from '../_shared/supabase.ts';
import { optionalEnv } from '../_shared/env.ts';
import { getTransport, type PushMessage } from '../_shared/notifications/transport.ts';

interface Body {
  event_key?: string;
  context?: Record<string, unknown>;
}

interface DispatchRow {
  notification_id: string;
  user_id: string;
  title: string;
  body: string | null;
  deep_link: string | null;
  payload: Record<string, unknown>;
  tokens: string[];
}

serve('send-push', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const secret = optionalEnv('NOTIFY_WEBHOOK_SECRET', '');
  if (secret && req.headers.get('x-webhook-secret') !== secret) {
    throw Forbidden('Secret webhook invalide');
  }

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (!body.event_key) throw BadRequest('event_key requis', 'missing_event_key');

  // 1) Résolution + écriture idempotente (toute la logique est en base).
  const db = createAdminClient();
  const { data, error } = await db.rpc('dispatch_notifications', {
    p_event_key: body.event_key,
    p_context: body.context ?? {},
  });
  if (error) throw rpcError(error);

  const result = data as { dispatched: number; push: DispatchRow[] };

  // 2) Transport (mock aujourd'hui, Expo/FCM/APNS/email/SMS demain).
  const messages: PushMessage[] = (result.push ?? []).map((r) => ({
    notificationId: r.notification_id,
    userId: r.user_id,
    title: r.title,
    body: r.body,
    deepLink: r.deep_link,
    payload: r.payload,
    tokens: r.tokens,
  }));
  const delivered = await getTransport().send(messages);

  return ok({ dispatched: result.dispatched, pushed: delivered.length });
});
