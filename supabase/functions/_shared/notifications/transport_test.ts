/**
 * Tests M8 — transport de notifications (mock) & sélection.
 * Offline. Lancer : deno test --allow-env supabase/functions/_shared/notifications/
 */
import { getTransport, MockExpoTransport, type PushMessage } from './transport.ts';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error('Assertion échouée: ' + msg);
}

const msg = (tokens: string[]): PushMessage => ({
  notificationId: 'n1',
  userId: 'u1',
  title: 'T',
  body: 'B',
  deepLink: 'app://mission/1',
  payload: {},
  tokens,
});

Deno.test('mock — envoie à tous les jetons, ok', async () => {
  const t = new MockExpoTransport();
  const res = await t.send([msg(['tok1', 'tok2']), msg([])]);
  assert(res.length === 2, '2 résultats');
  assert(res[0].ok && res[0].delivered === 2, '2 jetons livrés');
  assert(res[1].delivered === 0, 'aucun jeton');
});

Deno.test('getTransport — défaut mock', () => {
  assert(getTransport().name === 'mock', 'transport par défaut = mock');
});
