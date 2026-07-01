/**
 * Tests M3 — assemblage de configuration, présentation, dossier, classifieur.
 * Offline (assertions maison). Lancer : deno test supabase/functions/_shared/intake/
 */
import {
  assembleConfig,
  buildDossier,
  keywordClassifier,
  present,
  type RawOption,
  type RawQuestion,
  type RawSet,
  toEngineConfig,
} from './config.ts';
import { compute } from '../engine/mod.ts';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error('Assertion échouée: ' + msg);
}
function assertEq<T>(a: T, b: T, msg: string): void {
  if (a !== b) {
    throw new Error(`${msg} — attendu ${JSON.stringify(b)}, obtenu ${JSON.stringify(a)}`);
  }
}

const SETS: RawSet[] = [
  { slug: 'groceries', sortOrder: 10, categorySlug: 'groceries' },
  { slug: 'generic', sortOrder: 0, categorySlug: null },
];
const QUESTIONS: RawQuestion[] = [
  {
    id: 'g1',
    setSlug: 'generic',
    key: 'details',
    type: 'text',
    sortOrder: 10,
    labelKey: 'q.generic.details.label',
    helpKey: null,
    visibleWhen: {},
    requiredWhen: { always: true },
    validation: {},
  },
  {
    id: 's1',
    setSlug: 'groceries',
    key: 'store',
    type: 'select',
    sortOrder: 10,
    labelKey: 'q.groceries.store.label',
    helpKey: null,
    visibleWhen: {},
    requiredWhen: {},
    validation: {},
  },
];
const OPTIONS: RawOption[] = [
  { questionId: 's1', value: 'delhaize', labelKey: 'opt.store.delhaize', sortOrder: 20 },
  { questionId: 's1', value: 'carrefour', labelKey: 'opt.store.carrefour', sortOrder: 10 },
];
const STRINGS: Record<string, string> = {
  'q.generic.details.label': 'Pouvez-vous préciser votre besoin ?',
  'q.groceries.store.label': 'Quelle enseigne ?',
  'opt.store.carrefour': 'Carrefour',
  'opt.store.delhaize': 'Delhaize',
};
const KEYWORDS = { groceries: ['lait', 'courses'] };

Deno.test('assembleConfig — résolution i18n, catégories, options triées', () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, STRINGS, KEYWORDS);
  assertEq(cfg.questions.length, 2, 'nb questions');
  assertEq(cfg.categorySlugs.length, 1, 'une catégorie active');
  assertEq(cfg.categorySlugs[0], 'groceries', 'slug catégorie');

  const store = cfg.questions.find((q) => q.key === 'store')!;
  assertEq(store.categorySlug, 'groceries', 'store rattaché à groceries');
  assertEq(store.label, 'Quelle enseigne ?', 'label résolu');
  assertEq(store.options.map((o) => o.value).join(','), 'carrefour,delhaize', 'options triées');
  assertEq(store.options[0].label, 'Carrefour', 'label option résolu');

  const details = cfg.questions.find((q) => q.key === 'details')!;
  assertEq(details.categorySlug, null, 'details générique');
});

Deno.test("assembleConfig — libellé manquant retombe sur la clé (pas d'erreur)", () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, {}, KEYWORDS);
  assertEq(cfg.questions[0].label, cfg.questions[0].label, 'pas de crash');
  assert(cfg.questions.some((q) => q.label === 'q.generic.details.label'), 'fallback clé');
});

Deno.test('toEngineConfig — regroupe par set, catégorie = slug', () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, STRINGS, KEYWORDS);
  const eng = toEngineConfig(cfg);
  assertEq(eng.sets.length, 2, '2 sets');
  const generic = eng.sets.find((s) => s.slug === 'generic')!;
  assertEq(generic.categoryId, null, 'generic categoryId null');
  const groceries = eng.sets.find((s) => s.slug === 'groceries')!;
  assertEq(groceries.categoryId, 'groceries', 'groceries categoryId = slug');
  // le moteur consomme bien cette config
  const r = compute(eng, {}, 'groceries');
  assertEq(r.next?.key ?? null, 'details', 'moteur : 1re question générique');
});

Deno.test('present — libellé, options, obligation contextuelle', () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, STRINGS, KEYWORDS);
  const details = cfg.questions.find((q) => q.key === 'details')!;
  const p = present(details, {});
  assertEq(p.required, true, 'details requis (always)');
  assertEq(p.label, 'Pouvez-vous préciser votre besoin ?', 'label présenté');
  const store = present(cfg.questions.find((q) => q.key === 'store')!, {});
  assertEq(store.required, false, 'store optionnel');
  assertEq(store.options.length, 2, 'options présentées');
});

Deno.test('buildDossier — réponses présentes, dédupliquées, ordonnées', () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, STRINGS, KEYWORDS);
  const dossier = buildDossier(cfg, {
    answers: { details: 'du lait', store: 'carrefour' },
    classification: 'groceries',
  });
  assertEq(dossier.classification, 'groceries', 'classification reportée');
  assertEq(dossier.entries.length, 2, '2 entrées répondues');
  assertEq(dossier.entries[0].key, 'details', 'ordre : générique avant groceries');
  assertEq(dossier.entries[0].label, 'Pouvez-vous préciser votre besoin ?', 'label dossier');
});

Deno.test('keywordClassifier — match déterministe, sinon null (P8)', () => {
  const cfg = assembleConfig(SETS, QUESTIONS, OPTIONS, STRINGS, KEYWORDS);
  assertEq(
    keywordClassifier.classify("J'ai oublié du LAIT", cfg),
    'groceries',
    'match insensible casse',
  );
  assertEq(
    keywordClassifier.classify('je dois faire des courses', cfg),
    'groceries',
    'autre mot-clé',
  );
  assertEq(
    keywordClassifier.classify("quelque chose d'inédit", cfg),
    null,
    'aucun match → null (générique)',
  );
});
