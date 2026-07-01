/**
 * Orchestrateur d'intake (M3) — un tour de dialogue et la clôture.
 *
 * Ne dépend que des interfaces (`IntakeStore`, `Classifier`) et du moteur pur :
 * déterministe et testable hors-ligne. Écrit l'état minimal + les tours, calcule
 * la prochaine question via `compute()`, et s'arrête à la soumission (P1 : la
 * création de mission et la décision appartiennent à l'opérateur, module M4).
 */
import { compute } from '../engine/mod.ts';
import { BadRequest, Conflict, NotFound, Unprocessable } from '../errors.ts';
import { buildDossier, present, toEngineConfig } from './config.ts';
import type {
  Classifier,
  ConversationRow,
  Dossier,
  IntakeCtx,
  IntakeStore,
  LoadedConfig,
  LoadedQuestion,
  NewTurn,
  TurnInput,
  TurnResult,
} from './types.ts';

export interface IntakeDeps {
  store: IntakeStore;
  classifier: Classifier;
}

/** Sérialise une valeur de réponse pour le contenu textuel d'un tour. */
function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

/** Résout la conversation (existante & possédée, ou nouvelle). */
async function resolveConversation(
  deps: IntakeDeps,
  ctx: IntakeCtx,
  input: TurnInput,
): Promise<ConversationRow> {
  if (input.conversationId) {
    const conv = await deps.store.getConversation(input.conversationId, ctx.clientId);
    if (!conv) throw NotFound('Conversation introuvable', 'conversation_not_found');
    if (conv.status !== 'active') {
      throw Conflict('Conversation déjà close', 'conversation_closed');
    }
    return conv;
  }
  return deps.store.createConversation(ctx.clientId, input.locale ?? 'fr');
}

/**
 * Joue un tour de dialogue : applique l'entrée (réponse OU message libre),
 * recalcule le déroulé, persiste l'état minimal et les tours, renvoie la suite.
 */
export async function runTurn(
  deps: IntakeDeps,
  ctx: IntakeCtx,
  input: TurnInput,
): Promise<TurnResult> {
  const conv = await resolveConversation(deps, ctx, input);
  const config = await deps.store.loadConfig(conv.locale);
  const state = conv.state;
  const turns: NewTurn[] = [];

  if (input.answer) {
    const q = config.questions.find((x) => x.key === input.answer!.key);
    if (!q) throw BadRequest('Question inconnue', 'unknown_question');
    state.answers[q.key] = input.answer.value;
    turns.push({
      conversationId: conv.id,
      role: 'user',
      content: stringifyValue(input.answer.value),
      slotKey: q.key,
    });
  } else if (input.message !== undefined) {
    const trimmed = input.message.trim();
    if (trimmed === '') throw BadRequest('Message vide', 'empty_message');
    const cls = deps.classifier.classify(trimmed, config);
    if (cls !== null) state.classification = cls;
    turns.push({ conversationId: conv.id, role: 'user', content: trimmed });
  }
  // (aucune entrée = reprise : on recalcule et on repose la même question)

  const result = compute(toEngineConfig(config), state.answers, state.classification);

  let summary: Dossier | null = null;
  if (result.next) {
    const p = present(nextLoaded(config, result.next.key), state.answers);
    turns.push({
      conversationId: conv.id,
      role: 'assistant',
      content: p.label,
      slotKey: p.key,
    });
  } else if (result.canSummarize) {
    summary = buildDossier(config, state);
    summary.conversationId = conv.id;
    turns.push({
      conversationId: conv.id,
      role: 'assistant',
      content: null,
      metadata: { summary: true },
    });
  }

  await deps.store.saveState(conv.id, state);
  if (turns.length > 0) await deps.store.appendTurns(turns);

  return {
    conversationId: conv.id,
    classification: state.classification,
    next: result.next ? present(nextLoaded(config, result.next.key), state.answers) : null,
    canSummarize: result.canSummarize,
    invalid: result.invalid.map((q) => q.key),
    summary,
  };
}

/** Retrouve la question chargée (présentation) à partir de sa clé. */
function nextLoaded(config: LoadedConfig, key: string): LoadedQuestion {
  const q = config.questions.find((x) => x.key === key);
  if (!q) throw new Error(`question absente de la config: ${key}`); // invariant interne
  return q;
}

/**
 * Clôture l'intake : revalide côté serveur (tout le requis satisfait), passe la
 * conversation à `submitted` et renvoie le dossier. NE crée AUCUNE mission ni
 * paiement (P1) — c'est le rôle de la revue opérateur (M4).
 */
export async function finalize(
  deps: IntakeDeps,
  ctx: IntakeCtx,
  conversationId: string,
): Promise<Dossier> {
  const conv = await deps.store.getConversation(conversationId, ctx.clientId);
  if (!conv) throw NotFound('Conversation introuvable', 'conversation_not_found');
  if (conv.status !== 'active') throw Conflict('Conversation déjà close', 'conversation_closed');

  const config = await deps.store.loadConfig(conv.locale);
  const result = compute(toEngineConfig(config), conv.state.answers, conv.state.classification);
  if (!result.canSummarize) {
    throw Unprocessable(
      `Dossier incomplet: ${result.requiredRemaining.map((q) => q.key).join(', ')}`,
      'incomplete',
    );
  }

  await deps.store.setStatus(conv.id, 'submitted');
  await deps.store.appendTurns([
    {
      conversationId: conv.id,
      role: 'system',
      content: 'submitted',
      metadata: { event: 'submit' },
    },
  ]);

  const dossier = buildDossier(config, conv.state);
  dossier.conversationId = conv.id;
  return dossier;
}
