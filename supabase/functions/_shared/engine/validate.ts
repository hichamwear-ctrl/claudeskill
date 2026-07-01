/**
 * Validation d'une réponse vis-à-vis de sa question (M2.3).
 * Réf. CONVERSATION_ENGINE §5.2 (garde-fou), §6 (informations manquantes).
 *
 * Pure et déterministe. Distingue trois états :
 *  - `missing` : aucune valeur exploitable (à demander / à re-demander) ;
 *  - `invalid` : valeur présente mais non conforme (type/options/contraintes) ;
 *  - `valid`   : valeur exploitable.
 *
 * Note P1 : cette validation est un GARDE-FOU (types, obligations, options fermées),
 * pas un jugement métier. Toute valeur extraite par l'IA repasse ici côté serveur.
 */
import type { AnswerState, AnswerValue, Question, Validation } from './types.ts';

/** Une valeur « manquante » : absente ou vide (chaîne blanche / tableau vide). */
export function isMissing(v: AnswerValue): boolean {
  if (v === undefined || v === null) return true;
  if (typeof v === 'string') return v.trim() === '';
  if (Array.isArray(v)) return v.length === 0;
  return false;
}

/** Applique les contraintes `validation` selon le type. Retourne true si conforme. */
function satisfiesConstraints(value: AnswerValue, v: Validation | undefined): boolean {
  if (!v) return true;
  if (typeof value === 'string') {
    if (v.minLen !== undefined && value.length < v.minLen) return false;
    if (v.maxLen !== undefined && value.length > v.maxLen) return false;
    if (v.pattern !== undefined) {
      let re: RegExp;
      try {
        re = new RegExp(v.pattern);
      } catch {
        return true; // pattern cassé côté données → ne bloque pas (fail-open borné)
      }
      if (!re.test(value)) return false;
    }
  }
  if (typeof value === 'number') {
    if (v.min !== undefined && value < v.min) return false;
    if (v.max !== undefined && value > v.max) return false;
  }
  return true;
}

/** Vérifie la cohérence de TYPE (et options fermées) d'une valeur présente. */
function isTypeValid(q: Question, value: AnswerValue): boolean {
  switch (q.type) {
    case 'number':
      return typeof value === 'number' && Number.isFinite(value);
    case 'boolean':
      return typeof value === 'boolean';
    case 'select':
      if (typeof value !== 'string') return false;
      return !q.options || q.options.length === 0 || q.options.includes(value);
    case 'multiselect': {
      if (!Array.isArray(value)) return false;
      if (!value.every((x) => typeof x === 'string')) return false;
      if (q.options && q.options.length > 0) {
        return value.every((x) => q.options!.includes(x));
      }
      return true;
    }
    case 'text':
    case 'address':
    case 'date':
    case 'time':
      return typeof value === 'string';
    case 'photo':
    case 'document':
      // Média : la présence (chemin Storage, string) suffit au niveau moteur.
      return typeof value === 'string';
    default:
      return false;
  }
}

/** Calcule l'état d'une réponse pour une question donnée. */
export function answerState(q: Question, value: AnswerValue): AnswerState {
  if (isMissing(value)) return 'missing';
  if (!isTypeValid(q, value)) return 'invalid';
  if (!satisfiesConstraints(value, q.validation)) return 'invalid';
  return 'valid';
}
