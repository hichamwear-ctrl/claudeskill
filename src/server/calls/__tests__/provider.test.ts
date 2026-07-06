import { describe, it, expect } from "vitest";
import { mockCallProvider } from "@/server/calls/mock";
import { createTwilioCallProvider } from "@/server/calls/twilio";

describe("mock call provider", () => {
  it("creates a room without a token (demo mode) and tears down cleanly", async () => {
    const res = await mockCallProvider.createCall({
      reservationId: "r1",
      initiatorId: "u1",
    });
    expect(res.provider).toBe("mock");
    expect(res.room).toContain("r1");
    expect(res.token).toBeUndefined();
    expect(res.note).toBeTruthy();
    await expect(mockCallProvider.endCall(res.room)).resolves.toBeUndefined();
  });
});

describe("twilio call provider seam", () => {
  it("builds a deterministic room name from the reservation", async () => {
    const provider = createTwilioCallProvider({
      accountSid: "AC",
      apiKey: "KEY",
      apiSecret: "SECRET",
    });
    expect(provider.name).toBe("twilio");
    const res = await provider.createCall({ reservationId: "r42", initiatorId: "u1" });
    expect(res.room).toBe("bh-r42");
    expect(res.provider).toBe("twilio");
  });
});
