import { describe, it, expect } from "vitest";
import { eurosToCents } from "./money-input";

describe("eurosToCents", () => {
  it("convertit en centimes entiers", () => {
    expect(eurosToCents("123,45")).toBe(12345);
    expect(eurosToCents("123.45")).toBe(12345);
    expect(eurosToCents("100")).toBe(10000);
    expect(eurosToCents("0,05")).toBe(5);
    expect(eurosToCents("0,5")).toBe(50);
    expect(eurosToCents("46 127,85")).toBe(4612785);
  });

  it("rejette les entrées invalides", () => {
    expect(eurosToCents("")).toBeNull();
    expect(eurosToCents("abc")).toBeNull();
    expect(eurosToCents("1,234")).toBeNull(); // plus de 2 décimales
    expect(eurosToCents("-5")).toBeNull();
  });
});
