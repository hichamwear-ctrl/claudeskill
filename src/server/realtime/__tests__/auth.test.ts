import { describe, it, expect, beforeAll } from "vitest";
import {
  canJoinReservationChannel,
  signChannelToken,
  verifyChannelToken,
} from "@/server/realtime/auth";

beforeAll(() => {
  process.env.REALTIME_CHANNEL_SECRET = "test-secret-0123456789abcdef";
});

const reservation = { clientId: "client-1", barberUserId: "barber-1" };

describe("canJoinReservationChannel (RBAC predicate)", () => {
  it("allows the owning client", () => {
    expect(
      canJoinReservationChannel({ userId: "client-1", role: "CLIENT" }, reservation),
    ).toBe(true);
  });

  it("allows the assigned barber", () => {
    expect(
      canJoinReservationChannel({ userId: "barber-1", role: "BARBER" }, reservation),
    ).toBe(true);
  });

  it("allows any ADMIN", () => {
    expect(
      canJoinReservationChannel({ userId: "someone", role: "ADMIN" }, reservation),
    ).toBe(true);
  });

  it("denies an unrelated client (no cross-role leak)", () => {
    expect(
      canJoinReservationChannel({ userId: "client-2", role: "CLIENT" }, reservation),
    ).toBe(false);
  });

  it("denies an unassigned barber", () => {
    expect(
      canJoinReservationChannel({ userId: "barber-2", role: "BARBER" }, reservation),
    ).toBe(false);
  });

  it("denies a barber when the reservation has none assigned", () => {
    expect(
      canJoinReservationChannel(
        { userId: "barber-1", role: "BARBER" },
        { clientId: "client-1", barberUserId: null },
      ),
    ).toBe(false);
  });
});

describe("channel token sign/verify", () => {
  it("verifies a freshly signed token", () => {
    const token = signChannelToken({ channel: "reservation:1", userId: "u1" });
    expect(verifyChannelToken(token, { channel: "reservation:1", userId: "u1" })).toBe(
      true,
    );
  });

  it("rejects a token for a different channel or user", () => {
    const token = signChannelToken({ channel: "reservation:1", userId: "u1" });
    expect(verifyChannelToken(token, { channel: "reservation:2", userId: "u1" })).toBe(
      false,
    );
    expect(verifyChannelToken(token, { channel: "reservation:1", userId: "u2" })).toBe(
      false,
    );
  });

  it("rejects a tampered signature", () => {
    const token = signChannelToken({ channel: "reservation:1", userId: "u1" });
    const tampered = `${token.split(".")[0]}.deadbeef`;
    expect(
      verifyChannelToken(tampered, { channel: "reservation:1", userId: "u1" }),
    ).toBe(false);
  });

  it("rejects an expired token", () => {
    const token = signChannelToken({ channel: "reservation:1", userId: "u1" }, -1);
    expect(
      verifyChannelToken(token, { channel: "reservation:1", userId: "u1" }),
    ).toBe(false);
  });
});
