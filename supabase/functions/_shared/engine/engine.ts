/**
 * Moteur conversationnel déterministe — FONCTION PURE (M2.3).
 * Réf. CONVERSATION_ENGINE §5.1, DATA_MODEL §4.5.
 *
 * `compute(config, answers, classification)` calcule le déroulé du dialogue à
 * partir de la seule donnée : union du set GÉNÉRIQUE (toujours actif) et du set de
 * la classification retenue, tri déterministe, filtrage par visibilité, puis
 * détection des questions en attente et requises.
 *
 * Propriétés (les tests M2.3 les vérifient) :
 *  - PURE : aucune IA, aucun réseau, aucune base, aucune horloge → rejouable.
 *  - Cohérence par construction : réponse à une question invisible = inerte (jamais
 *    effacée) ; réponse invalide = re-posée ; changement de classification =
 *    recomposition des sets (les réponses génériques persistent). Aucun « rollback ».
 */
import { isRequired, isVisible } from './conditions.ts';
import { answerState } from './validate.ts';
import type { Answers, EngineConfig, EngineResult, Question } from './types.ts';

/** Ordre déterministe : (set.sort_order, question.sort_order, id). */
function compareQuestions(a: Question, b: Question): number {
  if (a.setSortOrder !== b.setSortOrder) return a.setSortOrder - b.setSortOrder;
  if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

/**
 * Sélectionne les sets actifs : le générique (`categoryId === null`) est TOUJOURS
 * actif ; s'ajoute le set dont la catégorie correspond à `classification`.
 * `classification === null` (P8 « je ne sais pas ») → générique seul.
 */
function activeQuestions(config: EngineConfig, classification: string | null): Question[] {
  return config.sets
    .filter((s) => s.categoryId === null || s.categoryId === classification)
    .flatMap((s) => s.questions)
    .sort(compareQuestions);
}

/**
 * Calcule le déroulé. `classification` = id de catégorie retenu, ou `null` pour le
 * parcours générique. Retourne la prochaine question, les requises restantes, les
 * invalides visibles, et si un récapitulatif est proposable.
 */
export function compute(
  config: EngineConfig,
  answers: Answers,
  classification: string | null,
): EngineResult {
  const questions = activeQuestions(config, classification);

  const invalid: Question[] = [];
  const pending: Question[] = [];
  const requiredRemaining: Question[] = [];

  for (const q of questions) {
    if (!isVisible(q, answers)) continue; // une réponse à une question cachée est inerte
    const state = answerState(q, answers[q.key]);
    const unsatisfied = state === 'missing' || state === 'invalid';

    if (state === 'invalid') invalid.push(q);
    if (unsatisfied) {
      pending.push(q);
      if (isRequired(q, answers)) requiredRemaining.push(q);
    }
  }

  return {
    next: pending.length > 0 ? pending[0] : null,
    requiredRemaining,
    invalid,
    canSummarize: requiredRemaining.length === 0,
  };
}
