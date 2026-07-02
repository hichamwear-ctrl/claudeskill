import { describe, expect, it } from '@jest/globals';

import type { PresentedQuestion } from '../types';
import { initialValue, validateAnswer } from '../validation';

function q(partial: Partial<PresentedQuestion>): PresentedQuestion {
  return { key: 'k', type: 'text', label: 'L', required: true, options: [], ...partial };
}

describe('initialValue', () => {
  it('donne une valeur neutre par type', () => {
    expect(initialValue(q({ type: 'multiselect' }))).toEqual([]);
    expect(initialValue(q({ type: 'boolean' }))).toBeNull();
    expect(initialValue(q({ type: 'text' }))).toBe('');
  });
});

describe('validateAnswer', () => {
  it('exige une valeur pour un texte requis', () => {
    expect(validateAnswer(q({ type: 'text', required: true }), '').ok).toBe(false);
    expect(validateAnswer(q({ type: 'text', required: true }), 'lait').ok).toBe(true);
  });

  it('valide un nombre requis', () => {
    expect(validateAnswer(q({ type: 'number', required: true }), 3).ok).toBe(true);
    expect(validateAnswer(q({ type: 'number', required: true }), null).ok).toBe(false);
  });

  it('exige au moins un choix en multiselect requis', () => {
    expect(validateAnswer(q({ type: 'multiselect', required: true }), []).ok).toBe(false);
    expect(validateAnswer(q({ type: 'multiselect', required: true }), ['a']).ok).toBe(true);
  });

  it('accepte le vide pour un champ optionnel', () => {
    expect(validateAnswer(q({ type: 'text', required: false }), null).ok).toBe(true);
  });
});
