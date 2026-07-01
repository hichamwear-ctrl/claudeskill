/**
 * Tests M2.3 — moteur conversationnel pur.
 *
 * Offline (aucun import distant) : assertions minimales définies ici.
 * Couvre : ordre déterministe, visibilité/obligation conditionnelles, validation
 * (types, options fermées, contraintes), invalidation & re-questionnement,
 * changement de direction (classification), reprise/idempotence, fail-closed,
 * inertie des réponses cachées, récapitulatif.
 *
 * Lancer : deno test supabase/functions/_shared/engine/
 */
import { compute } from './engine.ts';
import { answerState } from './validate.ts';
import { evalCondition, isRequired, isVisible } from './conditions.ts';
import type { Answers, EngineConfig, Question, QuestionSet } from './types.ts';

// --- micro-asserts (offline) -------------------------------------------------
function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error('Assertion échouée: ' + msg);
}
function assertEq<T>(a: T, b: T, msg: string): void {
  if (a !== b) {
    throw new Error(`${msg} — attendu ${JSON.stringify(b)}, obtenu ${JSON.stringify(a)}`);
  }
}
function nextKey(cfg: EngineConfig, answers: Answers, cls: string | null): string | null {
  return compute(cfg, answers, cls).next?.key ?? null;
}

// --- fixtures : miroir simplifié du seed (générique + groceries) -------------
function q(p: Partial<Question> & Pick<Question, 'id' | 'key' | 'type'>): Question {
  return {
    setSlug: p.setSlug ?? 'generic',
    setSortOrder: p.setSortOrder ?? 0,
    sortOrder: p.sortOrder ?? 0,
    ...p,
  };
}

const GENERIC: QuestionSet = {
  slug: 'generic',
  categoryId: null,
  sortOrder: 0,
  questions: [
    q({ id: 'g1', key: 'details', type: 'text', sortOrder: 10, requiredWhen: { always: true } }),
    q({ id: 'g2', key: 'address', type: 'address', sortOrder: 20, requiredWhen: { always: true } }),
    q({ id: 'g3', key: 'when', type: 'text', sortOrder: 30 }),
    q({ id: 'g4', key: 'photo', type: 'photo', sortOrder: 40 }),
  ],
};

const GROCERIES: QuestionSet = {
  slug: 'groceries',
  categoryId: 'cat-groceries',
  sortOrder: 10,
  questions: [
    q({
      id: 's1',
      key: 'store',
      type: 'select',
      setSlug: 'groceries',
      setSortOrder: 10,
      sortOrder: 10,
      options: ['carrefour', 'delhaize', 'colruyt', 'other'],
    }),
    q({
      id: 's2',
      key: 'items',
      type: 'text',
      setSlug: 'groceries',
      setSortOrder: 10,
      sortOrder: 20,
      requiredWhen: { always: true },
      validation: { maxLen: 500 },
    }),
    q({
      id: 's3',
      key: 'budget',
      type: 'number',
      setSlug: 'groceries',
      setSortOrder: 10,
      sortOrder: 30,
      validation: { min: 0 },
    }),
  ],
};

const CFG: EngineConfig = { sets: [GROCERIES, GENERIC] }; // ordre d'entrée volontairement inversé

// --- T1 : ordre déterministe (générique d'abord malgré l'ordre d'entrée) -----
Deno.test('T1 ordre déterministe — 1re question = details (générique, sort 10)', () => {
  assertEq(nextKey(CFG, {}, null), 'details', 'next initial');
});

// --- T2 : progression générique jusqu'au récapitulatif -----------------------
Deno.test('T2 progression générique — requis satisfaits → canSummarize', () => {
  let a: Answers = {};
  assertEq(nextKey(CFG, a, null), 'details', 'étape 1');
  a = { ...a, details: 'du lait' };
  assertEq(nextKey(CFG, a, null), 'address', 'étape 2');
  a = { ...a, address: 'rue X 1' };
  // 'when' et 'photo' optionnels → pending mais non requis
  const r = compute(CFG, a, null);
  assert(r.canSummarize, 'récap proposable une fois les requis remplis');
  assertEq(r.requiredRemaining.length, 0, 'aucun requis restant');
  assertEq(r.next?.key ?? null, 'when', 'optionnels encore proposés comme next');
});

// --- T3 : changement de direction — classification ajoute le set groceries ---
Deno.test('T3 direction — classer groceries ajoute ses questions, garde le générique', () => {
  const a: Answers = { details: 'courses', address: 'rue X 1' };
  // sans classification : requis générique OK
  assert(compute(CFG, a, null).canSummarize, 'générique complet');
  // avec groceries : 'items' (requis) manque → next=store (sort 10) puis items
  const r = compute(CFG, a, 'cat-groceries');
  assert(!r.canSummarize, 'groceries introduit un requis manquant (items)');
  // ordre : set générique (sort 0) AVANT groceries (sort 10) → 'when' (générique
  // optionnel) reste la prochaine question ; les questions groceries suivent.
  assertEq(r.next?.key ?? null, 'when', 'ordre : générique avant groceries');
  assert(r.requiredRemaining.some((x) => x.key === 'items'), 'items requis');
  // les réponses génériques persistent (details/address restent valides)
  assert(!r.requiredRemaining.some((x) => x.key === 'details'), 'details toujours satisfait');
});

// --- T4 : invalidation — une valeur invalide est re-demandée -----------------
Deno.test('T4 invalidation — select hors options → invalid & re-posé (ordre)', () => {
  // 'store' a une valeur invalide ; il figure dans `invalid` et sera reposé.
  const a: Answers = { details: 'x', address: 'y', store: 'auchan', items: 'pain' };
  const r = compute(CFG, a, 'cat-groceries');
  assert(r.invalid.some((x) => x.key === 'store'), 'store invalide (hors options)');
  // 'when'/'photo' (générique) restent pending avant groceries ; store reposé après.
  const filled: Answers = { ...a, when: 'demain', photo: 'p.jpg' };
  assertEq(
    nextKey(CFG, filled, 'cat-groceries'),
    'store',
    'store reposé une fois les optionnels génériques traités',
  );
});

Deno.test('T4b invalidation — number négatif viole min:0', () => {
  const a: Answers = { details: 'x', address: 'y', items: 'pain', budget: -5 };
  const r = compute(CFG, a, 'cat-groceries');
  assert(r.invalid.some((x) => x.key === 'budget'), 'budget invalide (min)');
});

// --- T5 : idempotence / reprise — mêmes entrées → même sortie ----------------
Deno.test('T5 idempotence — reprise déterministe', () => {
  const a: Answers = { details: 'x' };
  const r1 = compute(CFG, a, null);
  const r2 = compute(CFG, a, null);
  assertEq(r1.next?.key ?? null, r2.next?.key ?? null, 'next stable');
  assertEq(r1.canSummarize, r2.canSummarize, 'canSummarize stable');
  assertEq(r1.requiredRemaining.length, r2.requiredRemaining.length, 'requis stable');
});

// --- T6 : visibilité conditionnelle & inertie des réponses cachées -----------
Deno.test('T6 visible_when — question conditionnelle apparaît puis disparaît', () => {
  const cond: QuestionSet = {
    slug: 'cond',
    categoryId: null,
    sortOrder: 0,
    questions: [
      q({ id: 'c1', key: 'has_pet', type: 'boolean', sortOrder: 10 }),
      q({
        id: 'c2',
        key: 'pet_name',
        type: 'text',
        sortOrder: 20,
        visibleWhen: { '==': [{ answer: 'has_pet' }, true] },
        requiredWhen: { always: true },
      }),
    ],
  };
  const cfg: EngineConfig = { sets: [cond] };
  // has_pet absent → pet_name caché, non requis
  let r = compute(cfg, {}, null);
  assertEq(r.next?.key ?? null, 'has_pet', 'pet_name caché tant que has_pet inconnu');
  assert(!r.requiredRemaining.some((x) => x.key === 'pet_name'), 'caché ⇒ non requis');
  // has_pet=true → pet_name visible et requis
  r = compute(cfg, { has_pet: true }, null);
  assertEq(r.next?.key ?? null, 'pet_name', 'pet_name devient la prochaine question');
  // has_pet=false → pet_name caché : une réponse résiduelle est INERTE
  r = compute(cfg, { has_pet: false, pet_name: 'Rex' }, null);
  assert(r.canSummarize, 'pet_name caché ⇒ inerte, ne bloque pas');
  assert(r.next === null, 'plus rien à demander');
});

// --- T7 : required_when dynamique -------------------------------------------
Deno.test('T7 required_when — obligation activée par une autre réponse', () => {
  const set: QuestionSet = {
    slug: 'r',
    categoryId: null,
    sortOrder: 0,
    questions: [
      q({ id: 'r1', key: 'gift', type: 'boolean', sortOrder: 10 }),
      q({
        id: 'r2',
        key: 'message',
        type: 'text',
        sortOrder: 20,
        requiredWhen: { '==': [{ answer: 'gift' }, true] },
      }),
    ],
  };
  const cfg: EngineConfig = { sets: [set] };
  assert(compute(cfg, { gift: false }, null).canSummarize, 'gift=false ⇒ message optionnel');
  assert(!compute(cfg, { gift: true }, null).canSummarize, 'gift=true ⇒ message requis');
});

// --- T8 : fail-closed — conditions malformées ne cassent pas le tour ---------
Deno.test('T8 fail-closed — opérateur inconnu → invisible / non requis', () => {
  const bad: Question = q({
    id: 'b1',
    key: 'x',
    type: 'text',
    sortOrder: 10,
    visibleWhen: { bogus: [1, 2] } as unknown as Record<string, unknown>,
  });
  assertEq(isVisible(bad, {}), false, 'visible_when cassé ⇒ non visible');
  const badReq: Question = q({
    id: 'b2',
    key: 'y',
    type: 'text',
    sortOrder: 20,
    requiredWhen: { bogus: true } as unknown as Record<string, unknown>,
  });
  assertEq(isRequired(badReq, {}), false, 'required_when cassé ⇒ non requis');
  // au niveau compute : la question cassée est ignorée, pas d'exception
  const cfg: EngineConfig = {
    sets: [{ slug: 's', categoryId: null, sortOrder: 0, questions: [bad] }],
  };
  const r = compute(cfg, {}, null);
  assert(r.next === null && r.canSummarize, 'tour non cassé, question invisible ignorée');
});

// --- T9 : évaluateur borné — liste blanche + contexte réponses ---------------
Deno.test('T9 conditions — opérateurs whitelist', () => {
  const a: Answers = { n: 10, s: 'carrefour', arr: ['a', 'b'] };
  assertEq(evalCondition({ '>': [{ answer: 'n' }, 5] }, a), true, '>');
  assertEq(evalCondition({ '<=': [{ answer: 'n' }, 10] }, a), true, '<=');
  assertEq(evalCondition({ '!=': [{ answer: 's' }, 'delhaize'] }, a), true, '!=');
  assertEq(evalCondition({ in: [{ answer: 's' }, ['carrefour', 'colruyt']] }, a), true, 'in');
  assertEq(evalCondition({ exists: 'n' }, a), true, 'exists présent');
  assertEq(evalCondition({ exists: 'absent' }, a), false, 'exists absent');
  assertEq(
    evalCondition({ all: [{ exists: 'n' }, { '>': [{ answer: 'n' }, 0] }] }, a),
    true,
    'all',
  );
  assertEq(evalCondition({ any: [{ exists: 'absent' }, { exists: 'n' }] }, a), true, 'any');
  assertEq(evalCondition({ not: { exists: 'absent' } }, a), true, 'not');
  assertEq(evalCondition({ always: true }, a), true, 'always');
});

Deno.test('T9b conditions — malformé / non numérique lèvent (fail-closed en amont)', () => {
  let threw = false;
  try {
    evalCondition({ '>': [{ answer: 's' }, 5] }, { s: 'x' });
  } catch {
    threw = true;
  }
  assert(threw, 'comparaison numérique sur non-nombre lève');
  threw = false;
  try {
    evalCondition({ '==': [1, 2], extra: 3 } as Record<string, unknown>, {});
  } catch {
    threw = true;
  }
  assert(threw, 'plusieurs opérateurs ⇒ lève');
});

// --- T10 : validation des types & options -----------------------------------
Deno.test('T10 answerState — types, options, contraintes', () => {
  const num = q({ id: 'n', key: 'n', type: 'number', validation: { min: 0, max: 100 } });
  assertEq(answerState(num, undefined), 'missing', 'number absent');
  assertEq(answerState(num, 'douze'), 'invalid', 'number texte');
  assertEq(answerState(num, 150), 'invalid', 'number > max');
  assertEq(answerState(num, 42), 'valid', 'number ok');

  const sel = q({ id: 's', key: 's', type: 'select', options: ['a', 'b'] });
  assertEq(answerState(sel, 'c'), 'invalid', 'select hors options');
  assertEq(answerState(sel, 'a'), 'valid', 'select ok');

  const multi = q({ id: 'm', key: 'm', type: 'multiselect', options: ['a', 'b', 'c'] });
  assertEq(answerState(multi, []), 'missing', 'multiselect vide = manquant');
  assertEq(answerState(multi, ['a', 'z']), 'invalid', 'multiselect valeur hors options');
  assertEq(answerState(multi, ['a', 'c']), 'valid', 'multiselect ok');

  const bool = q({ id: 'b', key: 'b', type: 'boolean' });
  assertEq(answerState(bool, 'true'), 'invalid', 'boolean chaîne');
  assertEq(answerState(bool, false), 'valid', 'boolean false = valide (présent)');

  const txt = q({ id: 't', key: 't', type: 'text', validation: { maxLen: 3 } });
  assertEq(answerState(txt, '   '), 'missing', 'texte blanc = manquant');
  assertEq(answerState(txt, 'abcd'), 'invalid', 'texte > maxLen');
  assertEq(answerState(txt, 'abc'), 'valid', 'texte ok');
});

// --- T11 : boolean false ne doit pas être « manquant » ----------------------
Deno.test('T11 boolean false — présent, ne bloque pas la complétude', () => {
  const set: QuestionSet = {
    slug: 'x',
    categoryId: null,
    sortOrder: 0,
    questions: [
      q({ id: 'q', key: 'agree', type: 'boolean', sortOrder: 10, requiredWhen: { always: true } }),
    ],
  };
  const cfg: EngineConfig = { sets: [set] };
  assert(compute(cfg, { agree: false }, null).canSummarize, 'agree=false satisfait le requis');
  assert(!compute(cfg, {}, null).canSummarize, 'agree absent ⇒ requis manquant');
});

// --- T12 : classification inconnue → générique seul (P8) ---------------------
Deno.test("T12 P8 — classification null n'active que le générique", () => {
  const r = compute(CFG, {}, null);
  // aucune question groceries ne doit apparaître
  const keys = [r.next?.key, ...r.requiredRemaining.map((x) => x.key)];
  assert(
    !keys.includes('store') && !keys.includes('items'),
    'pas de question groceries en générique',
  );
});
