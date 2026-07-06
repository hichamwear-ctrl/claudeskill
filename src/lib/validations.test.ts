import { describe, it, expect } from "vitest";
import {
  registerSchema,
  confirmBarberSchema,
  reportSchema,
  barberProfileSchema,
} from "@/lib/validations";

const base = {
  firstName: "Jean",
  lastName: "Dupont",
  email: "jean@example.com",
  password: "password123",
  confirmPassword: "password123",
};

describe("registerSchema — account type", () => {
  it("accepts a minimal client sign-up", () => {
    const r = registerSchema.safeParse({ ...base, role: "CLIENT" });
    expect(r.success).toBe(true);
  });

  it("rejects a barber sign-up missing the dossier", () => {
    const r = registerSchema.safeParse({ ...base, role: "BARBER" });
    expect(r.success).toBe(false);
    if (!r.success) {
      const paths = r.error.issues.map((i) => i.path.join("."));
      expect(paths).toEqual(
        expect.arrayContaining(["phone", "social", "yearsExperience", "level", "bio"]),
      );
    }
  });

  it("accepts a complete barber dossier", () => {
    const r = registerSchema.safeParse({
      ...base,
      role: "BARBER",
      phone: "+32470000000",
      social: "@barber",
      yearsExperience: 5,
      level: "EXPERT",
      bio: "Expert coupe & barbe.",
    });
    expect(r.success).toBe(true);
  });

  it("still enforces password confirmation", () => {
    const r = registerSchema.safeParse({
      ...base,
      confirmPassword: "different",
    });
    expect(r.success).toBe(false);
  });
});

describe("confirmBarberSchema", () => {
  it("only allows CONFIRM or REFUSE", () => {
    expect(confirmBarberSchema.safeParse({ decision: "CONFIRM" }).success).toBe(true);
    expect(confirmBarberSchema.safeParse({ decision: "MAYBE" }).success).toBe(false);
  });
});

describe("reportSchema", () => {
  it("requires a type and a message", () => {
    expect(
      reportSchema.safeParse({ type: "PROBLEM", message: "Souci" }).success,
    ).toBe(true);
    expect(reportSchema.safeParse({ type: "PROBLEM", message: "" }).success).toBe(
      false,
    );
  });
});

describe("barberProfileSchema", () => {
  it("coerces years of experience and validates the level", () => {
    const r = barberProfileSchema.safeParse({ yearsExperience: "7", level: "CONFIRME" });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.yearsExperience).toBe(7);
  });
});
