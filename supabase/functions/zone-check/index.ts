/**
 * Edge Function `zone-check` — couverture & horaires (M4).
 * Réf. API_SPEC §4.2, BUSINESS_RULES BR-011/012/022.
 *
 * Thin wrapper sur la RPC `zone_check` (ST_Covers + service_windows). Aucun effet
 * de bord ; hors zone → l'app propose la `waitlist`.
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { rpcError } from '../_shared/rpc.ts';
import { createUserClient } from '../_shared/supabase.ts';
import { requireUser } from '../_shared/auth.ts';

interface Body {
  lat?: number;
  lng?: number;
  at?: string;
}

serve('zone-check', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const db = createUserClient(req);
  await requireUser(db, req);

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (typeof body.lat !== 'number' || typeof body.lng !== 'number') {
    throw BadRequest('lat/lng requis', 'missing_coordinates');
  }

  const { data, error } = await db.rpc('zone_check', {
    p_lng: body.lng,
    p_lat: body.lat,
    p_at: body.at ?? null,
  });
  if (error) throw rpcError(error);
  return ok(data);
});
