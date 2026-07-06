import { describe, it, expect } from "vitest";
import {
  BARBER_NEXT_STATUS,
  awaitsClientConfirmation,
  isConfirmed,
  isGpsActive,
  isConversationActive,
  isOrderFinished,
  statusProgress,
} from "@/lib/status";

describe("Phase 5 acceptance workflow transitions", () => {
  it("a barber accepts an open request → ACCEPTEE only", () => {
    expect(BARBER_NEXT_STATUS.DEMANDE_ENVOYEE).toEqual(["ACCEPTEE"]);
  });

  it("a barber cannot self-advance while awaiting client confirmation", () => {
    // ACCEPTEE → BARBER_ATTRIBUE is the client's decision, not a barber move.
    expect(BARBER_NEXT_STATUS.ACCEPTEE).not.toContain("BARBER_ATTRIBUE");
  });

  it("only lets the barber go en route from a confirmed booking", () => {
    expect(BARBER_NEXT_STATUS.BARBER_ATTRIBUE).toContain("EN_ROUTE");
    expect(BARBER_NEXT_STATUS.EN_ROUTE).toEqual(["ARRIVE"]);
  });
});

describe("conversation / gps / confirmation windows", () => {
  it("flags awaiting-confirmation only at ACCEPTEE", () => {
    expect(awaitsClientConfirmation("ACCEPTEE")).toBe(true);
    expect(awaitsClientConfirmation("BARBER_ATTRIBUE")).toBe(false);
  });

  it("treats the booking as confirmed from BARBER_ATTRIBUE onward", () => {
    expect(isConfirmed("DEMANDE_ENVOYEE")).toBe(false);
    expect(isConfirmed("ACCEPTEE")).toBe(false);
    expect(isConfirmed("BARBER_ATTRIBUE")).toBe(true);
    expect(isConfirmed("EN_ROUTE")).toBe(true);
    expect(isConfirmed("ANNULEE")).toBe(false);
  });

  it("shares GPS only while en route", () => {
    expect(isGpsActive("EN_ROUTE")).toBe(true);
    expect(isGpsActive("BARBER_ATTRIBUE")).toBe(false);
    expect(isGpsActive("ARRIVE")).toBe(false);
  });

  it("opens chat/calls from confirmation until arrival", () => {
    expect(isConversationActive("BARBER_ATTRIBUE")).toBe(true);
    expect(isConversationActive("EN_ROUTE")).toBe(true);
    // Closes on arrival.
    expect(isConversationActive("ARRIVE")).toBe(false);
    expect(isConversationActive("ACCEPTEE")).toBe(false);
  });

  it("shows the rating page after arrival", () => {
    expect(isOrderFinished("ARRIVE")).toBe(true);
    expect(isOrderFinished("EN_COURS")).toBe(true);
    expect(isOrderFinished("TERMINEE")).toBe(true);
    expect(isOrderFinished("EN_ROUTE")).toBe(false);
  });
});

describe("statusProgress", () => {
  it("is 0 for a cancelled order and 100 at completion", () => {
    expect(statusProgress("ANNULEE")).toBe(0);
    expect(statusProgress("TERMINEE")).toBe(100);
  });
});
