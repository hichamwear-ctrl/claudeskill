/**
 * Edge Function `review` — revue opérateur : claim + décision (M4).
 * Réf. API_SPEC §4.4b/§4.5, BUSINESS_RULES §2, LEAN_V1 (review absorbe
 * review-claim + review-request).
 *
 * Une seule surface, paramétrée par `action` :
 *   claim | release          → claim_review (verrou anti double-traitement)
 *   accept | reject | need_info → transition_mission (décision humaine, P1)
 *
 * Appelé AVEC le JWT de l'opérateur : les RPC (SECURITY DEFINER) lisent le rôle et
 * l'uid depuis le JWT et appliquent claim/rôle/allow-list côté base.
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { rpcError } from '../_shared/rpc.ts';
import { createUserClient } from '../_shared/supabase.ts';
import { requireRole, requireUser } from '../_shared/auth.ts';

type Action = 'claim' | 'release' | 'accept' | 'reject' | 'need_info';

interface Body {
  mission_id?: string;
  action?: Action;
  reason?: string;
  price?: number;
  eta_min?: number;
}

const TO_STATUS: Record<'accept' | 'reject' | 'need_info', string> = {
  accept: 'accepted',
  reject: 'rejected',
  need_info: 'needs_information',
};

serve('review', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const db = createUserClient(req);
  const auth = await requireUser(db, req);
  requireRole(auth, 'operator', 'admin');

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (!body.mission_id) throw BadRequest('mission_id requis', 'missing_mission_id');
  if (!body.action) throw BadRequest('action requise', 'missing_action');

  if (body.action === 'claim' || body.action === 'release') {
    const { data, error } = await db.rpc('claim_review', {
      p_mission_id: body.mission_id,
      p_release: body.action === 'release',
    });
    if (error) throw rpcError(error);
    return ok(data);
  }

  const to = TO_STATUS[body.action as 'accept' | 'reject' | 'need_info'];
  if (!to) throw BadRequest('action inconnue', 'invalid_action');
  if ((body.action === 'reject' || body.action === 'need_info') && !body.reason?.trim()) {
    throw BadRequest('motif requis', 'missing_reason');
  }

  const { data, error } = await db.rpc('transition_mission', {
    p_mission_id: body.mission_id,
    p_to: to,
    p_reason: body.reason ?? null,
    p_price: body.price ?? null,
    p_eta_min: body.eta_min ?? null,
  });
  if (error) throw rpcError(error);
  return ok(data);
});
