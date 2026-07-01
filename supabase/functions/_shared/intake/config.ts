/**
 * Assemblage de la configuration d'intake + adaptateurs de présentation (M3).
 *
 * Fonctions PURES (aucun accès base/réseau) : le `SupabaseStore` fournit les lignes
 * brutes, ici on les assemble en `LoadedConfig`, on en dérive l'`EngineConfig` pour
 * le moteur pur, et on construit le rendu (question présentée, dossier).
 * Testable hors-ligne.
 */
import { isRequired } from '../engine/mod.ts';
import type { Answers, EngineConfig, Question, QuestionSet } from '../engine/types.ts';
import type {
  Classifier,
  ConversationState,
  Dossier,
  LoadedConfig,
  LoadedQuestion,
  PresentedQuestion,
} from './types.ts';

// --- Lignes brutes (telles que fournies par le store) ------------------------
export interface RawSet {
  slug: string;
  sortOrder: number;
  categorySlug: string | null;
}
export interface RawQuestion {
  id: string;
  setSlug: string;
  key: string;
  type: string;
  sortOrder: number;
  labelKey: string;
  helpKey: string | null;
  visibleWhen: Record<string, unknown>;
  requiredWhen: Record<string, unknown>;
  validation: Record<string, unknown>;
}
export interface RawOption {
  questionId: string;
  value: string;
  labelKey: string;
  sortOrder: number;
}

/**
 * Assemble la configuration d'intake pour une locale.
 * `strings` = table content_strings de la locale (key → texte) ; libellé manquant
 * → on retombe sur la clé (jamais d'erreur bloquante à ce niveau).
 */
export function assembleConfig(
  sets: RawSet[],
  questions: RawQuestion[],
  options: RawOption[],
  strings: Record<string, string>,
  keywords: Record<string, string[]>,
): LoadedConfig {
  const resolve = (key: string): string => strings[key] ?? key;
  const setBySlug = new Map(sets.map((s) => [s.slug, s]));

  const optionsByQuestion = new Map<string, { value: string; label: string; sort: number }[]>();
  for (const o of options) {
    const arr = optionsByQuestion.get(o.questionId) ?? [];
    arr.push({ value: o.value, label: resolve(o.labelKey), sort: o.sortOrder });
    optionsByQuestion.set(o.questionId, arr);
  }

  const loaded: LoadedQuestion[] = questions.map((q) => {
    const set = setBySlug.get(q.setSlug);
    const opts = (optionsByQuestion.get(q.id) ?? [])
      .sort((a, b) => a.sort - b.sort)
      .map(({ value, label }) => ({ value, label }));
    return {
      id: q.id,
      key: q.key,
      type: q.type as LoadedQuestion['type'],
      setSlug: q.setSlug,
      setSortOrder: set?.sortOrder ?? 0,
      sortOrder: q.sortOrder,
      categorySlug: set?.categorySlug ?? null,
      visibleWhen: q.visibleWhen ?? {},
      requiredWhen: q.requiredWhen ?? {},
      validation: q.validation ?? {},
      label: resolve(q.labelKey),
      help: q.helpKey ? resolve(q.helpKey) : undefined,
      options: opts,
    };
  });

  const categorySlugs = [
    ...new Set(sets.map((s) => s.categorySlug).filter((s): s is string => !!s)),
  ];
  return { questions: loaded, categorySlugs, keywords };
}

/** Convertit une question chargée en question du moteur pur (logique seule). */
function toEngineQuestion(q: LoadedQuestion): Question {
  return {
    id: q.id,
    key: q.key,
    type: q.type,
    setSlug: q.setSlug,
    setSortOrder: q.setSortOrder,
    sortOrder: q.sortOrder,
    visibleWhen: q.visibleWhen,
    requiredWhen: q.requiredWhen,
    validation: q.validation,
    options: q.options.map((o) => o.value),
  };
}

/** Dérive l'`EngineConfig` (groupé par set) attendu par `compute()`. */
export function toEngineConfig(config: LoadedConfig): EngineConfig {
  const bySet = new Map<string, QuestionSet>();
  for (const q of config.questions) {
    let set = bySet.get(q.setSlug);
    if (!set) {
      set = {
        slug: q.setSlug,
        categoryId: q.categorySlug,
        sortOrder: q.setSortOrder,
        questions: [],
      };
      bySet.set(q.setSlug, set);
    }
    set.questions.push(toEngineQuestion(q));
  }
  return { sets: [...bySet.values()] };
}

/** Rendu API d'une question (libellé, aide, obligation contextuelle, options). */
export function present(q: LoadedQuestion, answers: Answers): PresentedQuestion {
  return {
    key: q.key,
    type: q.type,
    label: q.label,
    help: q.help,
    required: isRequired(toEngineQuestion(q), answers),
    options: q.options,
  };
}

/** Construit le récapitulatif : réponses présentes, dans l'ordre du dialogue. */
export function buildDossier(config: LoadedConfig, state: ConversationState): Dossier {
  const ordered = [...config.questions].sort((a, b) =>
    a.setSortOrder - b.setSortOrder || a.sortOrder - b.sortOrder || (a.id < b.id ? -1 : 1)
  );
  const seen = new Set<string>();
  const entries = [];
  for (const q of ordered) {
    if (seen.has(q.key)) continue;
    const value = state.answers[q.key];
    if (value === undefined || value === null || value === '') continue;
    seen.add(q.key);
    entries.push({ key: q.key, label: q.label, value, type: q.type });
  }
  return { conversationId: '', classification: state.classification, entries };
}

/**
 * Classifieur V1 : mots-clés déterministe (piloté par `app_config`, éditable).
 * Renvoie le 1er slug de catégorie dont un mot-clé apparaît dans le texte
 * (recherche insensible à la casse), sinon `null` (P8 → parcours générique).
 * Ordre stable : parcourt `categorySlugs` (ordre du référentiel).
 */
export const keywordClassifier: Classifier = {
  classify(text: string, config: LoadedConfig): string | null {
    const haystack = text.toLowerCase();
    for (const slug of config.categorySlugs) {
      const words = config.keywords[slug] ?? [];
      for (const w of words) {
        if (w && haystack.includes(w.toLowerCase())) return slug;
      }
    }
    return null;
  },
};
