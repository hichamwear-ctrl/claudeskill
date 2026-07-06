import { describe, it, expect } from "vitest";
import { barberLevelLabel, starString, BARBER_LEVELS } from "@/lib/barber";

describe("barber level labels", () => {
  it("maps every level to a French label", () => {
    expect(barberLevelLabel("JUNIOR")).toBe("Junior");
    expect(barberLevelLabel("CONFIRME")).toBe("Confirmé");
    expect(barberLevelLabel("EXPERT")).toBe("Expert");
  });

  it("covers all enum keys", () => {
    expect(Object.keys(BARBER_LEVELS)).toEqual(["JUNIOR", "CONFIRME", "EXPERT"]);
  });
});

describe("starString", () => {
  it("renders filled + empty stars totalling five", () => {
    expect(starString(5)).toBe("★★★★★");
    expect(starString(0)).toBe("☆☆☆☆☆");
    expect(starString(3)).toBe("★★★☆☆");
  });

  it("rounds to the nearest star", () => {
    expect(starString(4.6)).toBe("★★★★★");
    expect(starString(4.4)).toBe("★★★★☆");
  });
});
