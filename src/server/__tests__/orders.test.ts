import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the server dependencies so the acceptance handshake can be exercised
// without a database or realtime backend. `vi.hoisted` lets the mock object be
// referenced inside the hoisted `vi.mock` factory.
const prismaMock = vi.hoisted(() => ({
  barber: { findUnique: vi.fn() },
  reservation: { findUnique: vi.fn(), update: vi.fn() },
}));
vi.mock("@/server/prisma", () => ({ prisma: prismaMock }));
vi.mock("@/server/notifications", () => ({ notify: vi.fn().mockResolvedValue(undefined) }));
vi.mock("@/server/realtime/publisher", () => ({
  publishReservationStatus: vi.fn().mockResolvedValue(undefined),
}));

import { acceptRequest, decideBarber, OrderError } from "@/server/orders";
import { notify } from "@/server/notifications";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("acceptRequest", () => {
  it("provisionally assigns the barber, sets ACCEPTEE and notifies the client", async () => {
    prismaMock.barber.findUnique.mockResolvedValue({
      id: "b1",
      user: { firstName: "Karim", lastName: "El Amrani" },
    });
    prismaMock.reservation.findUnique.mockResolvedValue({
      id: "r1",
      status: "DEMANDE_ENVOYEE",
      barberId: null,
      declinedBarberIds: [],
      clientId: "c1",
    });
    prismaMock.reservation.update.mockResolvedValue({ id: "r1", status: "ACCEPTEE" });

    const res = await acceptRequest("r1", "barberUser");

    expect(prismaMock.reservation.update).toHaveBeenCalledWith({
      where: { id: "r1" },
      data: { status: "ACCEPTEE", barberId: "b1" },
    });
    expect(notify).toHaveBeenCalledWith(
      "c1",
      expect.objectContaining({ title: "Demande acceptée" }),
    );
    expect(res.status).toBe("ACCEPTEE");
  });

  it("refuses a request that was already taken", async () => {
    prismaMock.barber.findUnique.mockResolvedValue({ id: "b1", user: {} });
    prismaMock.reservation.findUnique.mockResolvedValue({
      id: "r1",
      status: "ACCEPTEE",
      barberId: "bX",
      declinedBarberIds: [],
      clientId: "c1",
    });
    await expect(acceptRequest("r1", "barberUser")).rejects.toBeInstanceOf(OrderError);
    expect(prismaMock.reservation.update).not.toHaveBeenCalled();
  });
});

describe("decideBarber", () => {
  const accepted = {
    id: "r1",
    status: "ACCEPTEE",
    clientId: "c1",
    barberId: "b1",
    reference: "REF123",
    barber: { userId: "barberUser", user: { firstName: "Karim" } },
  };

  it("CONFIRM validates the booking (BARBER_ATTRIBUE) and notifies the barber", async () => {
    prismaMock.reservation.findUnique.mockResolvedValue(accepted);
    prismaMock.reservation.update.mockResolvedValue({ id: "r1", status: "BARBER_ATTRIBUE" });

    const res = await decideBarber("r1", "c1", "CONFIRM");

    expect(prismaMock.reservation.update).toHaveBeenCalledWith({
      where: { id: "r1" },
      data: { status: "BARBER_ATTRIBUE" },
    });
    expect(notify).toHaveBeenCalledWith(
      "barberUser",
      expect.objectContaining({ title: "Barber confirmé" }),
    );
    expect(res.status).toBe("BARBER_ATTRIBUE");
  });

  it("REFUSE re-opens the request and excludes the refused barber", async () => {
    prismaMock.reservation.findUnique.mockResolvedValue(accepted);
    prismaMock.reservation.update.mockResolvedValue({ id: "r1", status: "DEMANDE_ENVOYEE" });

    await decideBarber("r1", "c1", "REFUSE");

    expect(prismaMock.reservation.update).toHaveBeenCalledWith({
      where: { id: "r1" },
      data: {
        status: "DEMANDE_ENVOYEE",
        barberId: null,
        declinedBarberIds: { push: "b1" },
      },
    });
  });

  it("rejects a decision from someone who is not the client", async () => {
    prismaMock.reservation.findUnique.mockResolvedValue(accepted);
    await expect(decideBarber("r1", "intruder", "CONFIRM")).rejects.toBeInstanceOf(
      OrderError,
    );
  });
});
