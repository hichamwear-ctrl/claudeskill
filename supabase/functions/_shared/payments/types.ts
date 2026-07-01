/**
 * Interface métier de paiement (M5) — le domaine ne connaît QUE cette interface.
 * Réf. SPEC §5, DATA_MODEL §5.2.
 *
 * Aujourd'hui : `MockPaymentProvider`. Demain : Stripe / Adyen / Mollie — même
 * interface, **aucun changement** du domaine (SQL) ni des Edge Functions métier.
 * Une `providerRef` est une chaîne OPAQUE (le domaine ne l'interprète jamais).
 */
export type PaymentAction = 'authorize' | 'capture' | 'void' | 'refund';

/** Données transmises au PSP pour une action (montant déjà borné par la base). */
export interface ProviderCall {
  paymentId: string;
  amount: number;
  currency: string;
}

/** Résultat normalisé d'un appel PSP. */
export interface PaymentResult {
  ok: boolean;
  providerRef: string;
  amount: number;
  status: string;
}

/** Contrat commun à toutes les implémentations (mock, Stripe…). */
export interface PaymentProvider {
  readonly name: string;
  authorize(call: ProviderCall): Promise<PaymentResult>;
  capture(call: ProviderCall): Promise<PaymentResult>;
  void(call: ProviderCall): Promise<PaymentResult>;
  refund(call: ProviderCall): Promise<PaymentResult>;
}
