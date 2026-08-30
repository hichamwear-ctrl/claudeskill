import { describe, it, expect } from "vitest";
import { monthNetRemainder, type MonthLine } from "./month.js";

describe("monthNetRemainder", () => {
  it("revenu seul, sans lignes", () => {
    expect(monthNetRemainder(3500000, [])).toBe(3500000);
  });

  it("additions et soustractions signées par le type", () => {
    const lines: MonthLine[] = [
      { amount: 50000, type: "SUBTRACTION" }, // essence
      { amount: 120000, type: "SUBTRACTION" }, // location
      { amount: 30000, type: "ADDITION" }, // CASA
    ];
    // 3500000 - 50000 - 120000 + 30000
    expect(monthNetRemainder(3500000, lines)).toBe(3360000);
  });

  it("plusieurs lignes TVA (−) et TVA récupérée (+) dans le même mois", () => {
    const lines: MonthLine[] = [
      { amount: 2100, type: "SUBTRACTION" }, // TVA #1
      { amount: 1736, type: "SUBTRACTION" }, // TVA #2
      { amount: 868, type: "ADDITION" }, // TVA récupérée #1
      { amount: 500, type: "ADDITION" }, // TVA récupérée #2
    ];
    // 1000000 - 2100 - 1736 + 868 + 500
    expect(monthNetRemainder(1000000, lines)).toBe(997532);
  });

  it("revenu à zéro", () => {
    expect(monthNetRemainder(0, [{ amount: 5000, type: "SUBTRACTION" }])).toBe(-5000);
  });

  it("ne mélange jamais le Kharja (aucun paramètre Kharja)", () => {
    // Signature volontairement limitée : uniquement revenu + lignes du mois.
    const lines: MonthLine[] = [{ amount: 300000, type: "SUBTRACTION" }];
    expect(monthNetRemainder(3500000, lines)).toBe(3200000);
  });

  it("rejette une ligne négative", () => {
    expect(() => monthNetRemainder(1000, [{ amount: -1, type: "ADDITION" }])).toThrow();
  });
});
