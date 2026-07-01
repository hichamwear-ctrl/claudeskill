/**
 * Tests M5 — MockPaymentProvider & sélection du provider.
 * Offline (assertions maison). Lancer : deno test supabase/functions/_shared/payments/
 */
import { MockPaymentProvider } from './mock.ts';
import { getProvider } from './provider.ts';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error('Assertion échouée: ' + msg);
}

Deno.test('mock authorize/capture/void/refund — ok + montant repris + réf préfixée', async () => {
  const p = new MockPaymentProvider();
  const call = { paymentId: 'pay-1', amount: 15.0, currency: 'eur' };

  const a = await p.authorize(call);
  assert(a.ok && a.amount === 15.0, 'authorize ok + montant');
  assert(a.providerRef.startsWith('sim_pi_'), 'réf autorisation sim_pi_');

  const c = await p.capture({ ...call, amount: 12.5 });
  assert(c.ok && c.amount === 12.5, 'capture ok + montant réel');

  const v = await p.void(call);
  assert(v.ok && v.status === 'canceled', 'void → canceled');

  const r = await p.refund({ ...call, amount: 12.5 });
  assert(r.ok && r.providerRef.startsWith('sim_re_'), 'refund → réf sim_re_');
});

Deno.test('mock — aucune donnée de carte, référence opaque unique', async () => {
  const p = new MockPaymentProvider();
  const r1 = await p.authorize({ paymentId: 'x', amount: 1, currency: 'eur' });
  const r2 = await p.authorize({ paymentId: 'x', amount: 1, currency: 'eur' });
  assert(r1.providerRef !== r2.providerRef, 'références uniques');
});

Deno.test('getProvider — défaut mock', () => {
  const p = getProvider();
  assert(p.name === 'mock', 'provider par défaut = mock');
});
