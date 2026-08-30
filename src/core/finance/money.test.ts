import { describe, it, expect } from "vitest";
import { assertCents, assertPositiveCents, formatEuros } from "./money";

describe("assertCents", () => {
  it("accepte un entier", () => {
    expect(assertCents(0)).toBe(0);
    expect(assertCents(-500)).toBe(-500);
    expect(assertCents(4612785)).toBe(4612785);
  });

  it("rejette un float (jamais de décimale en centimes)", () => {
    expect(() => assertCents(10.5)).toThrow();
    expect(() => assertCents(NaN)).toThrow();
    expect(() => assertCents(Infinity)).toThrow();
  });
});

describe("assertPositiveCents", () => {
  it("rejette un négatif", () => {
    expect(() => assertPositiveCents(-1)).toThrow();
  });
  it("accepte zéro", () => {
    expect(assertPositiveCents(0)).toBe(0);
  });
});

describe("formatEuros", () => {
  it("formate avec séparateur de milliers et 2 décimales", () => {
    expect(formatEuros(4612785)).toBe("46 127,85 €");
    expect(formatEuros(0)).toBe("0,00 €");
    expect(formatEuros(5)).toBe("0,05 €");
    expect(formatEuros(100)).toBe("1,00 €");
    expect(formatEuros(2336750)).toBe("23 367,50 €");
  });

  it("gère les montants négatifs", () => {
    expect(formatEuros(-300000)).toBe("-3 000,00 €");
  });
});
