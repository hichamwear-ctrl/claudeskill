import "server-only";
import type { PaymentProvider } from "./provider";
import { mockPaymentProvider } from "./mock";
import { createStripeProvider } from "./stripe";

let cached: PaymentProvider | null = null;

/** Stripe when configured, otherwise the inline mock provider (no charges). */
export function getPaymentProvider(): PaymentProvider {
  if (cached) return cached;
  const key = process.env.STRIPE_SECRET_KEY;
  cached = key ? createStripeProvider(key) : mockPaymentProvider;
  return cached;
}

export type { PaymentProvider } from "./provider";
