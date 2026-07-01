/**
 * Edge Function `converse` — un tour du dialogue d'intake (M3).
 * Réf. CONVERSATION_ENGINE, API_SPEC.
 *
 * Entrée : { conversation_id?, message?, answer?: {key,value}, locale? }.
 * Sortie : { conversation_id, classification, next, can_summarize, invalid, summary }.
 *
 * Auth : utilisateur authentifié (le client agit pour lui-même). L'écriture de la
 * conversation se fait en service_role (aucun grant client — M2.2) ; la PROPRIÉTÉ
 * est vérifiée en code (filtrage par client_id). L'IA (classification) est un
 * adaptateur remplaçable ; V1 = classifieur par mots-clés déterministe.
 */
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { BadRequest } from '../_shared/errors.ts';
import { createAdminClient, createUserClient } from '../_shared/supabase.ts';
import { requireUser } from '../_shared/auth.ts';
import { keywordClassifier } from '../_shared/intake/config.ts';
import { SupabaseStore } from '../_shared/intake/store.ts';
import { runTurn } from '../_shared/intake/orchestrator.ts';
import type { AnswerValue } from '../_shared/engine/types.ts';

interface Body {
  conversation_id?: string;
  message?: string;
  answer?: { key: string; value: AnswerValue };
  locale?: string;
}

serve('converse', async (req, _ctx) => {
  if (req.method !== 'POST') throw BadRequest('Méthode non supportée', 'method_not_allowed');

  const auth = await requireUser(createUserClient(req), req);

  let body: Body;
  try {
    body = await req.json();
  } catch {
    throw BadRequest('Corps JSON invalide', 'invalid_json');
  }
  if (body.answer && (typeof body.answer.key !== 'string')) {
    throw BadRequest('answer.key requis', 'invalid_answer');
  }

  const store = new SupabaseStore(createAdminClient());
  const result = await runTurn(
    { store, classifier: keywordClassifier },
    { clientId: auth.userId },
    {
      conversationId: body.conversation_id,
      message: body.message,
      answer: body.answer,
      locale: body.locale,
    },
  );

  return ok(result);
});
