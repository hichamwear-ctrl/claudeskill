/**
 * Moteur conversationnel OPÉRATIONNEL — types d'intégration (M3).
 * Réf. CONVERSATION_ENGINE, DATA_MODEL §4.5, API_SPEC (converse / submit-request).
 *
 * Ces types font le pont entre :
 *  - le **moteur pur** (`../engine/`), qui ne connaît que des clés/structures ;
 *  - la **donnée** (tables question_sets/questions/options/content_strings/app_config) ;
 *  - l'**API** (Edge Functions converse / submit-request).
 *
 * La logique d'orchestration (`orchestrator.ts`) ne dépend que des INTERFACES
 * ci-dessous (`IntakeStore`, `Classifier`) : elle est donc testable hors-ligne
 * avec des implémentations factices, et l'IA reste un adaptateur remplaçable.
 */
import type { Answers, AnswerValue, Condition, QuestionType, Validation } from '../engine/types.ts';

/** État minimal persité dans `conversations.state` (cf. DATA_MODEL §4.5). */
export interface ConversationState {
  answers: Answers;
  /** Slug de catégorie retenu (proposition), ou `null` = parcours générique (P8). */
  classification: string | null;
}

/** Ligne `conversations` telle que manipulée par l'orchestrateur. */
export interface ConversationRow {
  id: string;
  clientId: string;
  status: 'active' | 'submitted' | 'abandoned' | 'expired';
  locale: string;
  state: ConversationState;
}

/** Un tour à écrire dans `conversation_turns` (append-only). */
export interface NewTurn {
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string | null;
  slotKey?: string | null;
  metadata?: Record<string, unknown>;
}

/**
 * Question telle que chargée depuis la base (logique + présentation réunies).
 * `categorySlug` = slug de la catégorie du set (via jointure) ou `null` (générique).
 */
export interface LoadedQuestion {
  id: string;
  key: string;
  type: QuestionType;
  setSlug: string;
  setSortOrder: number;
  sortOrder: number;
  categorySlug: string | null;
  visibleWhen: Condition;
  requiredWhen: Condition;
  validation: Validation;
  /** Libellé résolu pour la locale (via content_strings). */
  label: string;
  help?: string;
  options: { value: string; label: string }[];
}

/** Configuration d'intake chargée pour une locale donnée. */
export interface LoadedConfig {
  questions: LoadedQuestion[];
  /** Slugs de catégories actives (référentiel de classification). */
  categorySlugs: string[];
  /** Mots-clés de classification par slug de catégorie (app_config, éditable). */
  keywords: Record<string, string[]>;
}

/** Question présentée au client (rendu API). */
export interface PresentedQuestion {
  key: string;
  type: QuestionType;
  label: string;
  help?: string;
  required: boolean;
  options: { value: string; label: string }[];
}

/** Une entrée du récapitulatif (dossier) transmis à la revue. */
export interface DossierEntry {
  key: string;
  label: string;
  value: AnswerValue;
  type: QuestionType;
}

/** Dossier structuré d'une demande (constitué par l'intake, décidé par l'opérateur). */
export interface Dossier {
  conversationId: string;
  classification: string | null;
  entries: DossierEntry[];
  /** Mission créée à la clôture (statut `pending_review`) — décision = opérateur (M4). */
  missionId?: string;
}

/** Entrée d'un tour de dialogue (API converse). */
export interface TurnInput {
  conversationId?: string;
  /** Message libre du client (1er intake ou écriture libre) → (re)classification. */
  message?: string;
  /** Réponse structurée à une question posée. */
  answer?: { key: string; value: AnswerValue };
  /** Locale à la création (défaut 'fr'). */
  locale?: string;
}

/** Résultat d'un tour de dialogue (API converse). */
export interface TurnResult {
  conversationId: string;
  classification: string | null;
  next: PresentedQuestion | null;
  canSummarize: boolean;
  /** Clés des réponses actuellement invalides (à corriger). */
  invalid: string[];
  /** Récapitulatif proposé quand tout le requis est satisfait. */
  summary: Dossier | null;
}

/** Contexte d'appel (utilisateur authentifié). */
export interface IntakeCtx {
  clientId: string;
}

/**
 * Seam de données : toute la persistance passe par cette interface.
 * Implémentée par `SupabaseStore` (prod) et par des factices (tests).
 * Les méthodes filtrant par `clientId` garantissent la propriété (le service_role
 * contourne la RLS : la vérification de propriété est faite ICI, en code).
 */
export interface IntakeStore {
  loadConfig(locale: string): Promise<LoadedConfig>;
  createConversation(clientId: string, locale: string): Promise<ConversationRow>;
  getConversation(id: string, clientId: string): Promise<ConversationRow | null>;
  saveState(id: string, state: ConversationState): Promise<void>;
  appendTurns(turns: NewTurn[]): Promise<void>;
  /**
   * Clôture ATOMIQUE : matérialise la mission `pending_review` depuis la
   * conversation et passe celle-ci à `submitted`. Retourne l'id de mission (M4).
   */
  submitConversation(id: string): Promise<string>;
}

/** Adaptateur de classification (IA remplaçable). V1 : mots-clés déterministe. */
export interface Classifier {
  /** Retourne un slug de catégorie, ou `null` si indéterminé (P8 : générique). */
  classify(text: string, config: LoadedConfig): string | null;
}
