import { describe, it, expect, vi } from "vitest";
import { InMemoryTransport } from "@/server/realtime/transport";

describe("InMemoryTransport", () => {
  it("delivers to matching channel + event only", async () => {
    const t = new InMemoryTransport();
    const hit = vi.fn();
    const missChannel = vi.fn();
    const missEvent = vi.fn();
    t.subscribe("reservation:1", "status", hit);
    t.subscribe("reservation:2", "status", missChannel);
    t.subscribe("reservation:1", "position", missEvent);

    await t.publish("reservation:1", "status", { reservationId: "1", status: "EN_ROUTE", at: 1 });

    expect(hit).toHaveBeenCalledOnce();
    expect(missChannel).not.toHaveBeenCalled();
    expect(missEvent).not.toHaveBeenCalled();
  });

  it("stops delivering after unsubscribe", async () => {
    const t = new InMemoryTransport();
    const fn = vi.fn();
    const sub = t.subscribe("reservation:1", "status", fn);
    sub.unsubscribe();
    await t.publish("reservation:1", "status", { reservationId: "1", status: "TERMINEE", at: 1 });
    expect(fn).not.toHaveBeenCalled();
  });
});
