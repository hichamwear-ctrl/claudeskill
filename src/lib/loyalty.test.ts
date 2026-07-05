import { describe, it, expect } from "vitest";
import {
  pointsForReservation,
  tierFor,
  maxRedeemableEuro,
  pointsForEuro,
  REDEEM_STEP_POINTS,
} from "@/lib/loyalty";

describe("pointsForReservation", () => {
  it("rounds the total to points", () => {
    expect(pointsForReservation(78)).toBe(78);
    expect(pointsForReservation(70.2)).toBe(70);
    expect(pointsForReservation(0)).toBe(0);
  });
});

describe("tierFor", () => {
  it("returns Bronze at 0 and computes the next tier gap", () => {
    const t = tierFor(0);
    expect(t.current.name).toBe("Bronze");
    expect(t.next?.name).toBe("Argent");
    expect(t.toNext).toBe(200);
  });
  it("upgrades tiers by threshold", () => {
    expect(tierFor(250).current.name).toBe("Argent");
    expect(tierFor(500).current.name).toBe("Or");
    expect(tierFor(5000).current.name).toBe("Platine");
    expect(tierFor(5000).next).toBeNull();
  });
});

describe("redemption math", () => {
  it("computes the largest redeemable voucher", () => {
    expect(maxRedeemableEuro(0)).toBe(0);
    expect(maxRedeemableEuro(250)).toBe(10); // 2 × 100 pts → 2 × 5€
  });
  it("maps euro back to a valid point cost", () => {
    expect(pointsForEuro(5)).toBe(REDEEM_STEP_POINTS);
    expect(pointsForEuro(10)).toBe(200);
    expect(pointsForEuro(7)).toBeNull(); // not a multiple of the step
    expect(pointsForEuro(0)).toBeNull();
  });
});
