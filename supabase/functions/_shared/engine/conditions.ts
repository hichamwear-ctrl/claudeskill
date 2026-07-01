/**
 * Évaluateur borné des conditions data-driven (`visible_when` / `required_when`).
 * Réf. CONVERSATION_ENGINE §5.5.
 *
 * Objectif : « chaque réponse influence les questions suivantes » SANS code.
 * Garanties :
 *  - **Liste blanche** d'opérateurs (aucune évaluation de code arbitraire).
 *  - **Contexte unique = les réponses** : ni horloge, ni aléa, ni réseau → pureté.
 *  - **Fail-closed** : toute expression inconnue/malformée lève une erreur, que les
 *    façades `isVisible`/`isRequired` interceptent pour renvoyer une valeur sûre.
 */
import type { Answers, AnswerValue, Condition, Question } from './types.ts';

/** Erreur interne d'évaluation (interceptée par les façades → fail-closed). */
class ConditionError extends Error {}

/** Une valeur est « présente » si non nulle/non vide (aligné sur `answerState`). */
function isPresent(v: AnswerValue): boolean {
  if (v === undefined || v === null) return false;
  if (typeof v === 'string') return v.trim() !== '';
  if (Array.isArray(v)) return v.length > 0;
  return true;
}

/** Vrai si `c` est un objet condition non vide. */
function isPlainObject(c: unknown): c is Record<string, unknown> {
  return typeof c === 'object' && c !== null && !Array.isArray(c);
}

/**
 * Résout un opérande : `{ "answer": "clé" }` → valeur de la réponse ;
 * toute autre valeur JSON (string/number/boolean/array) est un **littéral**.
 */
function resolveOperand(operand: unknown, answers: Answers): unknown {
  if (isPlainObject(operand) && 'answer' in operand) {
    const key = operand['answer'];
    if (typeof key !== 'string') throw new ConditionError('answer key must be a string');
    if (Object.keys(operand).length !== 1) throw new ConditionError('malformed answer ref');
    return answers[key];
  }
  return operand;
}

/** Compare deux opérandes numériquement (fail-closed si non numériques). */
function numericCompare(
  args: unknown,
  answers: Answers,
  cmp: (a: number, b: number) => boolean,
): boolean {
  if (!Array.isArray(args) || args.length !== 2) {
    throw new ConditionError('binary op expects [a, b]');
  }
  const a = resolveOperand(args[0], answers);
  const b = resolveOperand(args[1], answers);
  if (typeof a !== 'number' || typeof b !== 'number') {
    throw new ConditionError('numeric comparison requires numbers');
  }
  return cmp(a, b);
}

/** Égalité stricte sur primitives (les tableaux ne sont pas comparés par `==`). */
function equals(args: unknown, answers: Answers): boolean {
  if (!Array.isArray(args) || args.length !== 2) throw new ConditionError('== expects [a, b]');
  const a = resolveOperand(args[0], answers);
  const b = resolveOperand(args[1], answers);
  if (Array.isArray(a) || Array.isArray(b) || isPlainObject(a) || isPlainObject(b)) {
    throw new ConditionError('== compares primitives only');
  }
  return a === b;
}

/**
 * Évalue une condition. Une condition = un objet à **exactement une** clé
 * (l'opérateur). Lève `ConditionError` sur tout ce qui sort de la liste blanche.
 */
export function evalCondition(cond: Condition, answers: Answers): boolean {
  if (!isPlainObject(cond)) throw new ConditionError('condition must be an object');
  const keys = Object.keys(cond);
  if (keys.length !== 1) throw new ConditionError('condition must have exactly one operator');
  const op = keys[0];
  const arg = (cond as Record<string, unknown>)[op];

  switch (op) {
    case 'always':
      return arg === true;

    case 'all': {
      if (!Array.isArray(arg)) throw new ConditionError('all expects an array');
      return arg.every((c) => evalCondition(c as Condition, answers));
    }
    case 'any': {
      if (!Array.isArray(arg)) throw new ConditionError('any expects an array');
      return arg.some((c) => evalCondition(c as Condition, answers));
    }
    case 'not': {
      if (Array.isArray(arg)) throw new ConditionError('not expects a single condition');
      return !evalCondition(arg as Condition, answers);
    }

    case '==':
      return equals(arg, answers);
    case '!=':
      return !equals(arg, answers);
    case '>':
      return numericCompare(arg, answers, (a, b) => a > b);
    case '>=':
      return numericCompare(arg, answers, (a, b) => a >= b);
    case '<':
      return numericCompare(arg, answers, (a, b) => a < b);
    case '<=':
      return numericCompare(arg, answers, (a, b) => a <= b);

    case 'in': {
      if (!Array.isArray(arg) || arg.length !== 2) {
        throw new ConditionError('in expects [value, list]');
      }
      const value = resolveOperand(arg[0], answers);
      const list = resolveOperand(arg[1], answers);
      if (!Array.isArray(list)) throw new ConditionError('in expects a list as 2nd arg');
      return list.includes(value as never);
    }

    case 'exists': {
      // `{ "exists": "clé" }` — vrai si la réponse est présente et non vide.
      if (typeof arg !== 'string') throw new ConditionError('exists expects a key string');
      return isPresent(answers[arg]);
    }

    default:
      throw new ConditionError(`unknown operator: ${op}`);
  }
}

/**
 * Une question est-elle VISIBLE ? Défaut = visible (`visible_when` absente/`{}`).
 * Fail-closed : condition cassée → **non visible** (on ne montre pas au hasard).
 */
export function isVisible(q: Question, answers: Answers): boolean {
  const c = q.visibleWhen;
  if (c === undefined || c === null || Object.keys(c).length === 0) return true;
  try {
    return evalCondition(c, answers);
  } catch {
    return false;
  }
}

/**
 * Une question est-elle REQUISE ? Défaut = optionnelle (`required_when` absente/`{}`).
 * Fail-closed : condition cassée → **non requise** (une règle cassée ne bloque pas
 * la soumission ; l'opérateur tranchera en revue — P1).
 */
export function isRequired(q: Question, answers: Answers): boolean {
  const c = q.requiredWhen;
  if (c === undefined || c === null || Object.keys(c).length === 0) return false;
  try {
    return evalCondition(c, answers);
  } catch {
    return false;
  }
}
