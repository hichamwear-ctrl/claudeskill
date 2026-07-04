import { prisma } from "./prisma";

/** Ensures a Barber profile exists for a user with the BARBER role. */
export async function ensureBarberProfile(userId: string) {
  return prisma.barber.upsert({
    where: { userId },
    update: {},
    create: { userId },
  });
}

export async function getBarberDashboard(userId: string) {
  const barber = await ensureBarberProfile(userId);

  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);
  const endOfDay = new Date();
  endOfDay.setHours(23, 59, 59, 999);

  const [openRequests, assigned, history, todayCount, revenue] =
    await Promise.all([
      // Open requests not yet assigned to any barber.
      prisma.reservation.findMany({
        where: { status: "DEMANDE_ENVOYEE", barberId: null },
        include: { persons: true, address: true, client: true },
        orderBy: { scheduledAt: "asc" },
      }),
      // Active reservations assigned to this barber.
      prisma.reservation.findMany({
        where: {
          barberId: barber.id,
          status: { notIn: ["TERMINEE", "ANNULEE"] },
        },
        include: { persons: true, address: true, client: true },
        orderBy: { scheduledAt: "asc" },
      }),
      prisma.reservation.findMany({
        where: { barberId: barber.id, status: "TERMINEE" },
        include: { persons: true, address: true },
        orderBy: { scheduledAt: "desc" },
        take: 15,
      }),
      prisma.reservation.count({
        where: {
          barberId: barber.id,
          scheduledAt: { gte: startOfDay, lte: endOfDay },
          status: { notIn: ["ANNULEE"] },
        },
      }),
      prisma.reservation.aggregate({
        where: { barberId: barber.id, status: "TERMINEE" },
        _sum: { total: true },
      }),
    ]);

  return {
    barber,
    openRequests,
    assigned,
    history,
    stats: {
      today: todayCount,
      revenue: revenue._sum.total ?? 0,
      rating: barber.rating,
      totalJobs: barber.totalJobs,
    },
  };
}
