/**
 * Tests M3 — orchestrateur d'intake (bout en bout, store en mémoire).
 * Offline (assertions maison, aucun réseau). Couvre : création + classification,
 * progression jusqu'au récapitulable, clôture (complète/incomplète/rejouée),
 * propriété (ownership), réponse invalide, reprise, reclassement libre.
 *
 * Lancer : deno test supabase/functions/_shared/intake/
 */
import { finalize, runTurn } from './orchestrator.ts';
import { keywordClassifier } from './config.ts';
import { HttpError } from '../errors.ts';
import type {
  ConversationRow,
  ConversationState,
  IntakeStore,
  LoadedConfig,
  LoadedQuestion,
  NewTurn,
} from './types.ts';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error('Assertion échouée: ' + msg);
}
function assertEq<T>(a: T, b: T, msg: string): void {
  if (a !== b) {
    throw new Error(`${msg} — attendu ${JSON.stringify(b)}, obtenu ${JSON.stringify(a)}`);
  }
}
async function expectStatus(
  fn: () => Promise<unknown>,
  status: number,
  msg: string,
): Promise<void> {
  try {
    await fn();
  } catch (e) {
    if (e instanceof HttpError) {
      assertEq(e.status, status, msg);
      return;
    }
    throw e;
  }
  throw new Error(`${msg} — aucune erreur levée`);
}

// --- config de test (générique + groceries) ---------------------------------
function q(
  p: Partial<LoadedQuestion> & Pick<LoadedQuestion, 'id' | 'key' | 'type'>,
): LoadedQuestion {
  return {
    setSlug: 'generic',
    setSortOrder: 0,
    sortOrder: 0,
    categorySlug: null,
    visibleWhen: {},
    requiredWhen: {},
    validation: {},
    label: p.key,
    options: [],
    ...p,
  };
}
function makeConfig(): LoadedConfig {
  return {
    categorySlugs: ['groceries'],
    keywords: { groceries: ['lait', 'courses'] },
    questions: [
      q({ id: 'g1', key: 'details', type: 'text', sortOrder: 10, requiredWhen: { always: true } }),
      q({
        id: 'g2',
        key: 'address',
        type: 'address',
        sortOrder: 20,
        requiredWhen: { always: true },
      }),
      q({ id: 'g3', key: 'when', type: 'text', sortOrder: 30 }),
      q({
        id: 's1',
        key: 'store',
        type: 'select',
        setSlug: 'groceries',
        setSortOrder: 10,
        sortOrder: 10,
        categorySlug: 'groceries',
        options: [{ value: 'carrefour', label: 'Carrefour' }],
      }),
      q({
        id: 's2',
        key: 'items',
        type: 'text',
        setSlug: 'groceries',
        setSortOrder: 10,
        sortOrder: 20,
        categorySlug: 'groceries',
        requiredWhen: { always: true },
        validation: { maxLen: 500 },
      }),
    ],
  };
}

// --- store en mémoire (implémente le seam IntakeStore) ----------------------
class InMemoryStore implements IntakeStore {
  conversations = new Map<string, ConversationRow>();
  turns: NewTurn[] = [];
  private seq = 0;
  constructor(private readonly config: LoadedConfig) {}
  loadConfig(): Promise<LoadedConfig> {
    return Promise.resolve(this.config);
  }
  createConversation(clientId: string, locale: string): Promise<ConversationRow> {
    const id = 'conv-' + (++this.seq);
    const row: ConversationRow = {
      id,
      clientId,
      status: 'active',
      locale,
      state: { answers: {}, classification: null },
    };
    this.conversations.set(id, structuredClone(row));
    return Promise.resolve(structuredClone(row));
  }
  getConversation(id: string, clientId: string): Promise<ConversationRow | null> {
    const c = this.conversations.get(id);
    if (!c || c.clientId !== clientId) return Promise.resolve(null);
    return Promise.resolve(structuredClone(c));
  }
  saveState(id: string, state: ConversationState): Promise<void> {
    const c = this.conversations.get(id);
    if (c) c.state = structuredClone(state);
    return Promise.resolve();
  }
  setStatus(id: string, status: ConversationRow['status']): Promise<void> {
    const c = this.conversations.get(id);
    if (c) c.status = status;
    return Promise.resolve();
  }
  appendTurns(turns: NewTurn[]): Promise<void> {
    this.turns.push(...turns);
    return Promise.resolve();
  }
}

const CLIENT = 'client-A';
function deps() {
  return { store: new InMemoryStore(makeConfig()), classifier: keywordClassifier };
}

Deno.test('création + classification par message → 1re question posée', async () => {
  const d = deps();
  const r = await runTurn(d, { clientId: CLIENT }, { message: "J'ai oublié du lait" });
  assertEq(r.classification, 'groceries', 'classé groceries via mot-clé');
  assertEq(r.next?.key ?? null, 'details', 'générique en premier');
  assertEq(r.canSummarize, false, 'incomplet');
  assert(
    d.store.turns.some((t) => t.role === 'user' && t.content === "J'ai oublié du lait"),
    'tour user',
  );
  assert(
    d.store.turns.some((t) => t.role === 'assistant' && t.slotKey === 'details'),
    'tour assistant',
  );
});

Deno.test('progression : requis satisfaits → canSummarize (optionnels encore proposés)', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  const id = s1.conversationId;
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'details', value: 'lait, pain' },
  });
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'address', value: 'Rue X 1' },
  });
  const r = await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'items', value: 'lait' },
  });
  assertEq(r.canSummarize, true, 'requis (details, address, items) satisfaits');
  assert(r.next !== null, 'optionnels (when/store) encore proposés');
  assert(['when', 'store'].includes(r.next!.key), 'prochaine = un optionnel');
});

Deno.test('clôture incomplète → 422 ; complète → submitted + dossier ; rejouée → 409', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  const id = s1.conversationId;
  await expectStatus(() => finalize(d, { clientId: CLIENT }, id), 422, 'dossier incomplet');

  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'details', value: 'lait' },
  });
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'address', value: 'Rue X' },
  });
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'items', value: 'lait' },
  });

  const dossier = await finalize(d, { clientId: CLIENT }, id);
  assertEq(dossier.classification, 'groceries', 'classification dans le dossier');
  assertEq(dossier.entries.length, 3, '3 réponses présentes');
  assertEq(d.store.conversations.get(id)!.status, 'submitted', 'statut submitted');
  assert(
    d.store.turns.some((t) => t.role === 'system' && t.content === 'submitted'),
    'tour système submit',
  );

  await expectStatus(() => finalize(d, { clientId: CLIENT }, id), 409, 'seconde clôture refusée');
});

Deno.test('propriété : un autre client ne peut ni continuer ni clôturer (404)', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  const id = s1.conversationId;
  await expectStatus(
    () =>
      runTurn(d, { clientId: 'client-B' }, {
        conversationId: id,
        answer: { key: 'details', value: 'x' },
      }),
    404,
    'runTurn autre client',
  );
  await expectStatus(() => finalize(d, { clientId: 'client-B' }, id), 404, 'finalize autre client');
});

Deno.test('réponse invalide → signalée, non retenue pour la complétude', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  const id = s1.conversationId;
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'details', value: 'lait' },
  });
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'address', value: 'Rue X' },
  });
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'items', value: 'lait' },
  });
  const r = await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'store', value: 'auchan' },
  });
  assert(r.invalid.includes('store'), 'store hors options signalé invalide');
});

Deno.test('question inconnue → 400', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  await expectStatus(
    () =>
      runTurn(d, { clientId: CLIENT }, {
        conversationId: s1.conversationId,
        answer: { key: 'zzz', value: 'x' },
      }),
    400,
    'clé de question inexistante',
  );
});

Deno.test('reprise (aucune entrée) → repose la même question, état inchangé', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: 'des courses' });
  const id = s1.conversationId;
  await runTurn(d, { clientId: CLIENT }, {
    conversationId: id,
    answer: { key: 'details', value: 'lait' },
  });
  const resume = await runTurn(d, { clientId: CLIENT }, { conversationId: id });
  assertEq(resume.next?.key ?? null, 'address', 'reprise : même question suivante');
  assertEq(resume.classification, 'groceries', 'classification conservée');
});

Deno.test('P8 puis reclassement : message sans mot-clé = générique, puis mot-clé = groceries', async () => {
  const d = deps();
  const s1 = await runTurn(d, { clientId: CLIENT }, { message: "quelque chose d'inédit" });
  assertEq(s1.classification, null, 'aucun mot-clé → générique (P8)');
  assertEq(s1.next?.key ?? null, 'details', 'générique quand même opérationnel');
  const s2 = await runTurn(d, { clientId: CLIENT }, {
    conversationId: s1.conversationId,
    message: 'en fait des courses',
  });
  assertEq(s2.classification, 'groceries', 'reclassement sur écriture libre');
});
