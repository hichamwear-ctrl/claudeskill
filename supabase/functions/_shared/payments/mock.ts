/**
 * `MockPaymentProvider` (V1) — aucun appel externe, aucune donnée de carte.
 * Réf. SPEC §5.2. Reproduit fidèlement les statuts Stripe (requires_capture →
 * succeeded/partially_captured → refunded ; canceled pour un void) et génère des
 * références simulées `sim_pi_…` / `sim_re_…`. Déterministe en comportement
 * (toujours `ok:true`), non déterministe seulement sur la référence aléatoire.
 */
import type { PaymentProvider, PaymentResult, ProviderCall } from './types.ts';

function ref(prefix: string): string {
  return `sim_${prefix}_${crypto.randomUUID().replace(/-/g, '').slice(0, 24)}`;
}

export class MockPaymentProvider implements PaymentProvider {
  readonly name = 'mock';

  authorize(call: ProviderCall): Promise<PaymentResult> {
    return Promise.resolve({
      ok: true,
      providerRef: ref('pi'),
      amount: call.amount,
      status: 'requires_capture',
    });
  }
  capture(call: ProviderCall): Promise<PaymentResult> {
    return Promise.resolve({
      ok: true,
      providerRef: ref('pi'),
      amount: call.amount,
      status: 'succeeded',
    });
  }
  void(call: ProviderCall): Promise<PaymentResult> {
    return Promise.resolve({
      ok: true,
      providerRef: ref('pi'),
      amount: call.amount,
      status: 'canceled',
    });
  }
  refund(call: ProviderCall): Promise<PaymentResult> {
    return Promise.resolve({
      ok: true,
      providerRef: ref('re'),
      amount: call.amount,
      status: 'refunded',
    });
  }
}
