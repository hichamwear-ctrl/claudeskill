import { describe, it, expect } from "vitest";
import { renderStatusNotification } from "@/server/notifications/templates";

describe("renderStatusNotification", () => {
  it("renders consistent copy across channels for a status", () => {
    const n = renderStatusNotification("EN_ROUTE", "abcdef123456");
    expect(n.title).toContain("ABCDEF");
    expect(n.title).toContain("En route");
    expect(n.email.subject).toContain("En route");
    expect(n.email.html).toContain(n.body);
    expect(n.sms.text).toContain("En route");
  });

  it("covers the terminal statuses without throwing", () => {
    for (const s of ["ACCEPTEE", "ARRIVE", "TERMINEE", "ANNULEE"] as const) {
      const n = renderStatusNotification(s, "ref00000");
      expect(n.title.length).toBeGreaterThan(0);
      expect(n.email.text.length).toBeGreaterThan(0);
    }
  });
});
