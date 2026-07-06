import { prisma } from "./prisma";

/** Ensures a Barber profile exists for a user with the BARBER role. */
export async function ensureBarberProfile(userId: string) {
  return prisma.barber.upsert({
    where: { userId },
    update: {},
    create: { userId },
  });
}

/**
 * Public-facing barber profile (Phase 5): identity, portfolio, bio, seniority,
 * rating and recent reviews. The client sees this only after a barber has
 * accepted their request.
 */
export async function getBarberPublicProfile(barberId: string) {
  const barber = await prisma.barber.findUnique({
    where: { id: barberId },
    include: {
      user: { select: { firstName: true, lastName: true, image: true } },
      photos: { orderBy: { createdAt: "desc" } },
      reviews: {
        orderBy: { createdAt: "desc" },
        take: 10,
        include: { author: { select: { firstName: true } } },
      },
      _count: { select: { reviews: true } },
    },
  });
  if (!barber) return null;

  return {
    id: barber.id,
    firstName: barber.user.firstName,
    lastName: barber.user.lastName,
    image: barber.user.image,
    bio: barber.bio,
    level: barber.level,
    yearsExperience: barber.yearsExperience,
    instagram: barber.instagram,
    snapchat: barber.snapchat,
    rating: barber.rating,
    reviewCount: barber._count.reviews,
    photos: barber.photos,
    reviews: barber.reviews,
  };
}

export type BarberPublicProfile = NonNullable<
  Awaited<ReturnType<typeof getBarberPublicProfile>>
>;

export async function getBarberDashboard(userId: string) {
  const barber = await ensureBarberProfile(userId);

  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);
  const endOfDay = new Date();
  endOfDay.setHours(23, 59, 59, 999);

  const [openRequests, assigned, history, todayCount, revenue] =
    await Promise.all([
      // Open requests not yet assigned, excluding those this barber declined.
      prisma.reservation.findMany({
        where: {
          status: "DEMANDE_ENVOYEE",
          barberId: null,
          NOT: { declinedBarberIds: { has: barber.id } },
        },
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
