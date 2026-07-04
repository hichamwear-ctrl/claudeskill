import { describe, it, expect, vi } from "vitest";
import { InMemoryTransport } from "@/server/realtime/transport";

describe("InMemoryTransport", () => {
  it("delivers a published event to a matching subscriber", async () => {
    const t = new InMemoryTransport();
    const handler = vi.fn();
    t.subscribe("reservation:1", "status", handler);

    await t.publish("reservation:1", "status", {
      reservationId: "1",
      status: "EN_ROUTE",
      at: 123,
    });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith({
      reservationId: "1",
      status: "EN_ROUTE",
      at: 123,
    });
  });

  it("does not deliver across channels or event names", async () => {
    const t = new InMemoryTransport();
    const wrongChannel = vi.fn();
    const wrongEvent = vi.fn();
    t.subscribe("reservation:2", "status", wrongChannel);
    t.subscribe("reservation:1", "position", wrongEvent);

    await t.publish("reservation:1", "status", {
      reservationId: "1",
      status: "ARRIVE",
      at: 1,
    });

    expect(wrongChannel).not.toHaveBeenCalled();
    expect(wrongEvent).not.toHaveBeenCalled();
  });

  it("stops delivering after unsubscribe()", async () => {
    const t = new InMemoryTransport();
    const handler = vi.fn();
    const sub = t.subscribe("reservation:1", "status", handler);
    sub.unsubscribe();

    await t.publish("reservation:1", "status", {
      reservationId: "1",
      status: "TERMINEE",
      at: 1,
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it("channel-level unsubscribe removes all handlers", async () => {
    const t = new InMemoryTransport();
    const handler = vi.fn();
    t.subscribe("reservation:1", "status", handler);
    t.unsubscribe("reservation:1");

    await t.publish("reservation:1", "status", {
      reservationId: "1",
      status: "ACCEPTEE",
      at: 1,
    });

    expect(handler).not.toHaveBeenCalled();
  });
});
