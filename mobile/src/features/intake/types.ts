/** DTO de l'intake — miroir des sorties Edge (converse / submit-request). */

export type AnswerValue = string | number | boolean | string[] | null;

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

export interface QuestionOption {
  value: string;
  label: string;
}

/** Question présentée par `converse` (label + options déjà résolus côté serveur). */
export interface PresentedQuestion {
  key: string;
  type: QuestionType;
  label: string;
  help?: string;
  required: boolean;
  options: QuestionOption[];
}

export interface DossierEntry {
  key: string;
  label: string;
  value: AnswerValue;
  type: QuestionType;
}

export interface Dossier {
  conversationId: string;
  classification: string | null;
  entries: DossierEntry[];
  missionId?: string;
}

/** Résultat d'un tour de `converse`. */
export interface TurnResult {
  conversationId: string;
  classification: string | null;
  next: PresentedQuestion | null;
  canSummarize: boolean;
  invalid: string[];
  summary: Dossier | null;
}

/** Retour de `zone-check`. */
export interface ZoneCheckResult {
  covered: boolean;
  zone_id: string | null;
  zone_slug?: string;
  open: boolean;
  next_window: { weekday: number; opens_at: string; closes_at: string } | null;
}

/** Retour de `estimate-price` (`price = null` pour les catégories sur devis). */
export interface PriceEstimate {
  price: number | null;
  eta_min: number;
  currency: string;
  zone_id: string | null;
  quote_only: boolean;
  breakdown: {
    base_fare: number;
    distance_km: number;
    price_per_km: number;
    distance_cost: number;
    minimum_price: number;
    category_base_fee: number;
  };
}
