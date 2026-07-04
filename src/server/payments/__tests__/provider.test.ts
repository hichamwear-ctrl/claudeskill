import { describe, it, expect } from "vitest";
import { mockPaymentProvider } from "@/server/payments/mock";

describe("mockPaymentProvider", () => {
  it("settles checkout inline (paid) without external calls", async () => {
    const r = await mockPaymentProvider.createCheckout({
      reservationId: "r1",
      amount: 78,
      currency: "EUR",
      description: "test",
      successUrl: "http://x/success",
      cancelUrl: "http://x/cancel",
    });
    expect(r.status).toBe("paid");
    expect(r.sessionId).toContain("r1");
    expect(r.url).toBeUndefined();
  });

  it("ignores webhooks", () => {
    expect(mockPaymentProvider.verifyWebhook("{}", null).type).toBe("ignored");
  });
});
