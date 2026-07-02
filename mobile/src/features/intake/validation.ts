import { z } from 'zod';

import type { AnswerValue, PresentedQuestion } from './types';

/** Construit un schéma Zod de validation à partir de la question présentée. */
export function buildSchema(q: PresentedQuestion): z.ZodType<AnswerValue> {
  switch (q.type) {
    case 'number': {
      const base = z.number({ message: 'Nombre requis' });
      return (q.required ? base : base.nullable()) as z.ZodType<AnswerValue>;
    }
    case 'boolean': {
      const base = z.boolean({ message: 'Réponse requise' });
      return (q.required ? base : base.nullable()) as z.ZodType<AnswerValue>;
    }
    case 'multiselect': {
      const base = z.array(z.string());
      return (q.required ? base.min(1, 'Sélection requise') : base) as z.ZodType<AnswerValue>;
    }
    case 'select': {
      const base = z.string();
      return (q.required ? base.min(1, 'Sélection requise') : base.nullable()) as z.ZodType<AnswerValue>;
    }
    default: {
      const base = z.string();
      return (q.required ? base.min(1, 'Ce champ est requis') : base.nullable()) as z.ZodType<AnswerValue>;
    }
  }
}

/** Valeur initiale neutre selon le type. */
export function initialValue(q: PresentedQuestion): AnswerValue {
  if (q.type === 'multiselect') return [];
  if (q.type === 'boolean') return null;
  return '';
}

export interface ValidationResult {
  ok: boolean;
  value?: AnswerValue;
  error?: string;
}

/** Valide une réponse et renvoie la valeur normalisée ou un message d'erreur. */
export function validateAnswer(q: PresentedQuestion, value: AnswerValue): ValidationResult {
  const parsed = buildSchema(q).safeParse(value);
  if (parsed.success) return { ok: true, value: parsed.data };
  return { ok: false, error: parsed.error.issues[0]?.message ?? 'Valeur invalide' };
}
