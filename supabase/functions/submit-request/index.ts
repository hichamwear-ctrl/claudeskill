/**
 * Edge Function `submit-request` — clôture de l'intake (M3).
 * Réf. CONVERSATION_ENGINE §2 (SUBMIT), API_SPEC.
 *
 * Revalide le dossier côté serveur (tout le requis satisfait), passe la
 * conversation à `submitted` et renvoie le dossier structuré.
 *
 * GARDE-FOU P1 : ne crée AUCUNE mission et ne déclenche AUCUN paiement.
 * La création de mission (pending_review) et la décision humaine relèvent de la
 * revue opérateur (module M4).
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { createAdminClient, createUserClient } from '../_shared/supabase.ts';
import { requireUser } from '../_shared/auth.ts';
import { keywordClassifier } from '../_shared/intake/config.ts';
import { SupabaseStore } from '../_shared/intake/store.ts';
import { finalize } from '../_shared/intake/orchestrator.ts';

interface Body {
  conversation_id?: string;
}

serve('submit-request', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const auth = await requireUser(createUserClient(req), req);

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (!body.conversation_id) throw BadRequest('conversation_id requis', 'missing_conversation_id');

  const store = new SupabaseStore(createAdminClient());
  const dossier = await finalize(
    { store, classifier: keywordClassifier },
    { clientId: auth.userId },
    body.conversation_id,
  );

  return ok(dossier);
});
