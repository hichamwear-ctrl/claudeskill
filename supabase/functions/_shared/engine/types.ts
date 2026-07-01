/**
 * Moteur conversationnel — types partagés (M2.3).
 *
 * Réf. CONVERSATION_ENGINE §3.1 / §5, DATA_MODEL §4.5, principes P0/P1/P8/P9/P10.
 *
 * Le moteur est une **FONCTION PURE** : à partir d'une CONFIGURATION (issue des
 * tables `question_sets`/`questions`/`question_options`, déjà normalisée par
 * l'appelant), des RÉPONSES accumulées et de la CLASSIFICATION retenue, il calcule
 * le déroulé du dialogue — sans IA, sans réseau, sans base, sans horloge.
 * Mêmes entrées → même sortie ; rejouable et testable indépendamment du modèle IA.
 *
 * Ces types ne portent AUCUN texte (les libellés vivent dans `content_strings`,
 * résolus ailleurs) : le moteur ne raisonne que sur des clés et des structures.
 */

/** Types de question (miroir de l'enum SQL `question_type`). */
export type QuestionType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'photo'
  | 'document'
  | 'address'
  | 'date'
  | 'time';

/** Valeur d'une réponse. `undefined`/`null`/`''`/`[]` = « non répondu ». */
export type AnswerValue = string | number | boolean | string[] | null | undefined;

/** Dictionnaire des réponses, indexé par `question.key`. */
export type Answers = Record<string, AnswerValue>;

/**
 * Condition data-driven (`visible_when` / `required_when`), évaluée par
 * l'évaluateur borné (`conditions.ts`). Structure JSON libre — validée à l'exécution.
 */
export type Condition = Record<string, unknown>;

/** Contraintes de validation d'une réponse (colonne `questions.validation`). */
export interface Validation {
  minLen?: number;
  maxLen?: number;
  min?: number;
  max?: number;
  /** Expression régulière (chaîne) appliquée aux réponses `text`/`address`. */
  pattern?: string;
}

/** Une question = un « slot » du dialogue. */
export interface Question {
  /** Identifiant stable (départage l'ordre de façon déterministe). */
  id: string;
  /** Clé métier, unique dans son set ; sert de clé de réponse. */
  key: string;
  type: QuestionType;
  /** Slug du set d'appartenance (traçabilité / débogage). */
  setSlug: string;
  /** Ordre du set (1er critère de tri). */
  setSortOrder: number;
  /** Ordre de la question dans le set (2e critère de tri). */
  sortOrder: number;
  visibleWhen?: Condition;
  requiredWhen?: Condition;
  validation?: Validation;
  /** Valeurs autorisées (select/multiselect). Vide/absent = non contraint. */
  options?: string[];
}

/** Un ensemble de questions, générique (categoryId=null) ou lié à une catégorie. */
export interface QuestionSet {
  slug: string;
  /** `null` = set GÉNÉRIQUE, toujours actif (P8/P11). */
  categoryId: string | null;
  sortOrder: number;
  questions: Question[];
}

/** Configuration complète fournie au moteur (déjà chargée depuis la base). */
export interface EngineConfig {
  sets: QuestionSet[];
}

/** État d'une réponse vis-à-vis de sa question. */
export type AnswerState = 'missing' | 'invalid' | 'valid';

/**
 * Résultat du calcul — tout est DÉRIVÉ, rien n'est stocké côté état.
 * - `next` : prochaine question à poser (ou `null` = plus rien à demander).
 * - `requiredRemaining` : questions requises visibles encore à satisfaire.
 * - `invalid` : questions visibles répondues mais dont la valeur est invalide.
 * - `canSummarize` : vrai si aucune question requise ne manque (→ récapitulatif).
 */
export interface EngineResult {
  next: Question | null;
  requiredRemaining: Question[];
  invalid: Question[];
  canSummarize: boolean;
}
