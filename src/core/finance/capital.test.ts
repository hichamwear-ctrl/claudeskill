import { describe, it, expect } from "vitest";
import { globalCapital, type KharjaLine } from "./capital";

describe("globalCapital", () => {
  it("somme des restes de mois, sans Kharja", () => {
    expect(globalCapital([3500000, 1200000], [])).toBe(4700000);
  });

  it("intègre l'effet net de tous les Kharja (entrées − sorties, tous mois confondus)", () => {
    const kharja: KharjaLine[] = [
      { type: "OUT", amount: 300000 }, // sortie Kharja de Février
      { type: "IN", amount: 100000 }, // entrée Kharja de Mars
    ];
    // (3500000) + (100000 - 300000)
    expect(globalCapital([3500000], kharja)).toBe(3300000);
  });

  it("accepte des restes de mois négatifs", () => {
    expect(globalCapital([-50000, 20000], [])).toBe(-30000);
  });

  it("liste vide -> 0", () => {
    expect(globalCapital([], [])).toBe(0);
  });

  it("le Kharja n'affecte QUE le capital global, pas le reste du mois", () => {
    const monthRemainder = 3500000; // déjà calculé sans Kharja
    const withKharja = globalCapital([monthRemainder], [{ type: "OUT", amount: 200000 }]);
    // le reste du mois reste 3500000 ; seul le global bouge
    expect(withKharja).toBe(3300000);
    expect(monthRemainder).toBe(3500000);
  });
});
