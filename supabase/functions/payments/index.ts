/**
 * Edge Function `payments` — adaptateur PSP (M5).
 * Réf. API_SPEC §4.6/§4.7/§4.8, LEAN_V1 (payments absorbe create-authorization /
 * capture-payment / refund).
 *
 * Orchestration « intent → PSP → settle », le domaine restant en base :
 *   1. `payment_intent` (JWT appelant) : GARDE P1 (accepté/propriété/rôle/état)
 *      + montant borné ;
 *   2. `PaymentProvider` (mock/Stripe) : appel PSP réel/simulé ;
 *   3. `payment_settle` (service_role) : enregistre + transition mission couplée.
 *
 * L'Edge est un SIMPLE ADAPTATEUR : aucun garde-fou métier ici (ils sont en SQL).
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { rpcError } from '../_shared/rpc.ts';
import { createAdminClient, createUserClient } from '../_shared/supabase.ts';
import { requireUser } from '../_shared/auth.ts';
import { getProvider } from '../_shared/payments/provider.ts';
import type { PaymentAction } from '../_shared/payments/types.ts';

interface Body {
  mission_id?: string;
  action?: PaymentAction;
  amount_final?: number; // capture : montant réel (≤ autorisé, revérifié en base)
  advance_actual?: number;
  proof_path?: string;
}

const ACTIONS: PaymentAction[] = ['authorize', 'capture', 'void', 'refund'];

serve('payments', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const db = createUserClient(req);
  const auth = await requireUser(db, req);

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (!body.mission_id) throw BadRequest('mission_id requis', 'missing_mission_id');
  if (!body.action || !ACTIONS.includes(body.action)) {
    throw BadRequest('action invalide', 'invalid_action');
  }
  if (body.action === 'capture' && !body.proof_path?.trim()) {
    throw BadRequest('proof_path requis pour la capture', 'missing_proof');
  }

  // 1) Garde-fou + préparation (JWT appelant → gate P1 en base).
  const intentRes = await db.rpc('payment_intent', {
    p_mission_id: body.mission_id,
    p_action: body.action,
  });
  if (intentRes.error) throw rpcError(intentRes.error);
  const intent = intentRes.data as { payment_id: string; amount: number; currency: string };

  // 2) Appel PSP (montant capturé = montant réel plafonné par la base au settle).
  const provider = getProvider();
  const amount = body.action === 'capture'
    ? Number(body.amount_final ?? intent.amount)
    : intent.amount;
  const result = await provider[body.action]({
    paymentId: intent.payment_id,
    amount,
    currency: intent.currency,
  });

  // 3) Enregistrement + transition mission couplée (service_role).
  const data: Record<string, unknown> = { amount: result.amount };
  if (body.action === 'capture') {
    data.advance_actual = body.advance_actual ?? null;
    data.proof_path = body.proof_path;
  }
  const settleRes = await createAdminClient().rpc('payment_settle', {
    p_payment_id: intent.payment_id,
    p_action: body.action,
    p_provider: provider.name,
    p_provider_ref: result.providerRef,
    p_ok: result.ok,
    p_actor: auth.userId,
    p_data: data,
  });
  if (settleRes.error) throw rpcError(settleRes.error);

  return ok(settleRes.data);
});
