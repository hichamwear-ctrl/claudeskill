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

describe("canJoinReservationChannel", () => {
  it("allows client, assigned barber and admin", () => {
    expect(canJoinReservationChannel({ userId: "client-1", role: "CLIENT" }, reservation)).toBe(true);
    expect(canJoinReservationChannel({ userId: "barber-1", role: "BARBER" }, reservation)).toBe(true);
    expect(canJoinReservationChannel({ userId: "x", role: "ADMIN" }, reservation)).toBe(true);
  });
  it("denies unrelated users (no cross-role leak)", () => {
    expect(canJoinReservationChannel({ userId: "client-2", role: "CLIENT" }, reservation)).toBe(false);
    expect(canJoinReservationChannel({ userId: "barber-2", role: "BARBER" }, reservation)).toBe(false);
  });
  it("denies a barber when none is assigned", () => {
    expect(
      canJoinReservationChannel(
        { userId: "barber-1", role: "BARBER" },
        { clientId: "client-1", barberUserId: null },
      ),
    ).toBe(false);
  });
});

describe("channel tokens", () => {
  it("round-trips a valid token", () => {
    const t = signChannelToken({ channel: "reservation:1", userId: "u1" });
    expect(verifyChannelToken(t, { channel: "reservation:1", userId: "u1" })).toBe(true);
  });
  it("rejects wrong channel/user, tampering and expiry", () => {
    const t = signChannelToken({ channel: "reservation:1", userId: "u1" });
    expect(verifyChannelToken(t, { channel: "reservation:2", userId: "u1" })).toBe(false);
    expect(verifyChannelToken(t, { channel: "reservation:1", userId: "u2" })).toBe(false);
    expect(verifyChannelToken(`${t.split(".")[0]}.bad`, { channel: "reservation:1", userId: "u1" })).toBe(false);
    const expired = signChannelToken({ channel: "reservation:1", userId: "u1" }, -1);
    expect(verifyChannelToken(expired, { channel: "reservation:1", userId: "u1" })).toBe(false);
  });
});
