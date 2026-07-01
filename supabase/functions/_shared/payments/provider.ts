/**
 * Sélection du `PaymentProvider` par configuration (SPEC §5).
 * `PAYMENT_PROVIDER = mock | stripe` (défaut : mock). Stripe branché plus tard
 * SANS toucher au domaine ni aux Edge Functions métier.
 */
import { optionalEnv } from '../env.ts';
import type { PaymentProvider } from './types.ts';
import { MockPaymentProvider } from './mock.ts';

export function getProvider(): PaymentProvider {
  const name = optionalEnv('PAYMENT_PROVIDER', 'mock');
  switch (name) {
    case 'mock':
      return new MockPaymentProvider();
    // case 'stripe': return new StripePaymentProvider(); // futur — même interface
    default:
      throw new Error(`PaymentProvider inconnu: ${name}`);
  }
}
