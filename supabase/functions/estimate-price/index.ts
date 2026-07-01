/**
 * Edge Function `estimate-price` — prix & ETA (M4).
 * Réf. API_SPEC §4.3, SPEC §3, BUSINESS_RULES BR-070/211.
 *
 * Thin wrapper sur la RPC `estimate_price` (PostGIS + pricing_rules). Aucun effet
 * de bord (le snapshot de prix est posé à la soumission/à l'acceptation).
 * Catégorie « sur devis » (metadata.quote_only) → `price = null` (fixé en revue).
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { rpcError } from '../_shared/rpc.ts';
import { createUserClient } from '../_shared/supabase.ts';
import { requireUser } from '../_shared/auth.ts';

interface Point {
  lat: number;
  lng: number;
}
interface Body {
  category_id?: string;
  dropoff?: Point;
  pickup?: Point;
}

function isPoint(p: unknown): p is Point {
  return !!p && typeof (p as Point).lat === 'number' && typeof (p as Point).lng === 'number';
}

serve('estimate-price', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const db = createUserClient(req);
  await requireUser(db, req);

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (!body.category_id) throw BadRequest('category_id requis', 'missing_category');
  if (!isPoint(body.dropoff)) throw BadRequest('dropoff {lat,lng} requis', 'missing_dropoff');
  if (body.pickup !== undefined && !isPoint(body.pickup)) {
    throw BadRequest('pickup {lat,lng} invalide', 'invalid_pickup');
  }

  const { data, error } = await db.rpc('estimate_price', {
    p_category_id: body.category_id,
    p_dropoff_lng: body.dropoff.lng,
    p_dropoff_lat: body.dropoff.lat,
    p_pickup_lng: body.pickup?.lng ?? null,
    p_pickup_lat: body.pickup?.lat ?? null,
  });
  if (error) throw rpcError(error);
  return ok(data);
});
