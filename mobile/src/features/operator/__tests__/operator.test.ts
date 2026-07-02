import { describe, expect, it } from '@jest/globals';

import { nextSteps } from '../steps';

describe('nextSteps', () => {
  it('propose des étapes cohérentes depuis assigned', () => {
    expect(nextSteps('assigned')).toContain('en_route');
  });
  it('mène en_route → arrived → in_progress', () => {
    expect(nextSteps('en_route')).toEqual(['arrived']);
    expect(nextSteps('arrived')).toEqual(['in_progress']);
  });
  it('ne propose plus d’étape en in_progress (clôture via capture)', () => {
    expect(nextSteps('in_progress')).toEqual([]);
    expect(nextSteps('completed')).toEqual([]);
  });
});
