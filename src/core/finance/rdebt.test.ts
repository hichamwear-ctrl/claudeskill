import { describe, it, expect } from "vitest";
import { transferNet, repaymentNet, rDebtBalance, type RDebtLine } from "./rdebt.js";

describe("transferNet (−8 %)", () => {
  it("exemple du cahier des charges : 180 € -> 165,60 €", () => {
    expect(transferNet(18000)).toBe(16560);
  });

  it("arrondit au centime le plus proche", () => {
    // 12345 × 0.92 = 11357.4 -> round 11357
    expect(transferNet(12345)).toBe(11357);
  });

  it("zéro reste zéro", () => {
    expect(transferNet(0)).toBe(0);
  });
});

describe("repaymentNet", () => {
  it("cash : net = brut", () => {
    expect(repaymentNet(18000, "CASH")).toBe(18000);
  });
  it("virement : net = brut × 0.92", () => {
    expect(repaymentNet(18000, "TRANSFER")).toBe(16560);
  });
});

describe("rDebtBalance", () => {
  it("base seule (seed initial 23 367,50 €)", () => {
    expect(rDebtBalance(2336750, [])).toBe(2336750);
  });

  it("avances (+) et remboursements nets (−)", () => {
    const lines: RDebtLine[] = [
      { type: "INCREASE", amountNet: 100000 }, // avance
      { type: "REPAYMENT", amountNet: 16560 }, // virement 180€ net
      { type: "REPAYMENT", amountNet: 50000 }, // cash 500€
    ];
    // 2336750 + 100000 - 16560 - 50000
    expect(rDebtBalance(2336750, lines)).toBe(2370190);
  });

  it("reste totalement isolé (aucun paramètre mois/Kharja dans la signature)", () => {
    // La fonction ne connaît que base + lignes R : impossible d'y injecter
    // un reste de mois ou une ligne Kharja.
    expect(rDebtBalance(0, [{ type: "INCREASE", amountNet: 5000 }])).toBe(5000);
  });

  it("rejette une base négative", () => {
    expect(() => rDebtBalance(-1, [])).toThrow();
  });
});
