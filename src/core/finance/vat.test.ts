import { describe, it, expect } from "vitest";
import { vatFromTotal, vat, recoveredVat } from "./vat";

describe("vatFromTotal", () => {
  it("cas exact (TTC = HT × 1.21)", () => {
    // 100,00 € HT -> 121,00 € TTC -> TVA = 21,00 €
    expect(vatFromTotal(12100)).toBe(2100);
  });

  it("arrondit le HTVA au centime le plus proche (Math.round)", () => {
    // 10000 / 1.21 = 8264,4628... -> round 8264 -> TVA 1736
    expect(vatFromTotal(10000)).toBe(1736);
    // 5000 / 1.21 = 4132,231... -> round 4132 -> TVA 868
    expect(vatFromTotal(5000)).toBe(868);
  });

  it("montant à zéro", () => {
    expect(vatFromTotal(0)).toBe(0);
  });

  it("rejette un total négatif ou non entier", () => {
    expect(() => vatFromTotal(-1)).toThrow();
    expect(() => vatFromTotal(100.5)).toThrow();
  });
});

describe("vat (bouton TVA, somme libre)", () => {
  it("somme les éléments cochés puis déduit la TVA", () => {
    // revenu 100000 + dépense 21000 = 121000 -> TVA
    // 121000 / 1.21 = 100000 -> TVA 21000
    expect(vat([100000, 21000])).toBe(21000);
  });

  it("liste vide -> 0", () => {
    expect(vat([])).toBe(0);
  });
});

describe("recoveredVat (bouton Récupérer TVA)", () => {
  it("applique la même formule que vat mais reste une fonction distincte", () => {
    expect(recoveredVat([12100])).toBe(2100);
    // même entrée -> même résultat que vatFromTotal, sans lien logique
    expect(recoveredVat([10000])).toBe(vatFromTotal(10000));
  });

  it("plusieurs sources (Essence + Location) sommées", () => {
    // 6000 + 4000 = 10000 -> 1736
    expect(recoveredVat([6000, 4000])).toBe(1736);
  });
});

describe("indépendance TVA / TVA récupérée sur une même dépense", () => {
  it("une même dépense peut alimenter les deux calculs séparément", () => {
    const essence = 6000;
    const tva = vat([essence]); // via bouton TVA
    const recup = recoveredVat([essence]); // via bouton Récupérer TVA
    // Aucune déduplication : les deux se calculent indépendamment et sont égaux ici
    expect(tva).toBe(recup);
    expect(tva).toBeGreaterThan(0);
  });
});
