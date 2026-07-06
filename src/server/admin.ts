import { prisma } from "./prisma";
import type { Prisma } from "@prisma/client";

/**
 * Order search for the admin panel: matches order number/reference, client
 * first/last name, phone, address (street / city / postal code) and barber name.
 */
export async function searchReservations(query: string) {
  const q = query.trim();
  const where: Prisma.ReservationWhereInput = q
    ? {
        OR: [
          { reference: { contains: q, mode: "insensitive" } },
          { client: { firstName: { contains: q, mode: "insensitive" } } },
          { client: { lastName: { contains: q, mode: "insensitive" } } },
          { client: { phone: { contains: q, mode: "insensitive" } } },
          { address: { street: { contains: q, mode: "insensitive" } } },
          { address: { city: { contains: q, mode: "insensitive" } } },
          { address: { postalCode: { contains: q, mode: "insensitive" } } },
          { barber: { user: { firstName: { contains: q, mode: "insensitive" } } } },
          { barber: { user: { lastName: { contains: q, mode: "insensitive" } } } },
        ],
      }
    : {};

  return prisma.reservation.findMany({
    where,
    include: {
      persons: true,
      client: true,
      address: true,
      barber: { include: { user: true } },
    },
    orderBy: { createdAt: "desc" },
    take: 50,
  });
}

/** Pending barber account applications (awaiting admin validation). */
export async function getBarberApplications() {
  return prisma.barber.findMany({
    where: { approvalStatus: "PENDING" },
    include: { user: true },
    orderBy: { createdAt: "asc" },
  });
}

/** Unresolved client reports (problems / help requests). */
export async function getOpenReports() {
  return prisma.report.findMany({
    where: { resolvedAt: null },
    include: {
      reporter: { select: { firstName: true, lastName: true } },
      barber: { include: { user: { select: { firstName: true, lastName: true } } } },
      reservation: { select: { reference: true } },
    },
    orderBy: { createdAt: "desc" },
  });
}

/** Approved barbers with moderation state + notes for the admin barbers page. */
export async function getBarbersForModeration() {
  return prisma.barber.findMany({
    where: { approvalStatus: "APPROVED" },
    include: {
      user: true,
      adminNotes: {
        orderBy: { createdAt: "desc" },
        include: { author: { select: { firstName: true } } },
      },
      _count: { select: { reviews: true, reservations: true } },
    },
    orderBy: { createdAt: "desc" },
  });
}

type ModerationAction =
  | "APPROVE"
  | "REFUSE"
  | "BAN"
  | "UNBAN"
  | "SUSPEND"
  | "UNSUSPEND"
  | "DELETE";

/** Applies an admin moderation action to a barber (and their account). */
export async function moderateBarber(barberId: string, action: ModerationAction) {
  const barber = await prisma.barber.findUnique({ where: { id: barberId } });
  if (!barber) throw new Error("Barber introuvable");

  switch (action) {
    case "APPROVE":
      return prisma.barber.update({
        where: { id: barberId },
        data: { approvalStatus: "APPROVED", isAvailable: true },
      });
    case "REFUSE":
      return prisma.barber.update({
        where: { id: barberId },
        data: { approvalStatus: "REFUSED", isAvailable: false },
      });
    case "BAN":
      return prisma.barber.update({
        where: { id: barberId },
        data: { bannedAt: new Date(), isAvailable: false },
      });
    case "UNBAN":
      return prisma.barber.update({
        where: { id: barberId },
        data: { bannedAt: null },
      });
    case "SUSPEND":
      return prisma.barber.update({
        where: { id: barberId },
        data: { suspendedAt: new Date(), isAvailable: false },
      });
    case "UNSUSPEND":
      return prisma.barber.update({
        where: { id: barberId },
        data: { suspendedAt: null },
      });
    case "DELETE":
      // Removing the user cascades to the barber profile and related rows.
      return prisma.user.delete({ where: { id: barber.userId } });
  }
}

export async function addAdminNote(
  barberId: string,
  authorId: string,
  body: string,
) {
  return prisma.adminNote.create({ data: { barberId, authorId, body } });
}

export async function resolveReport(reportId: string) {
  return prisma.report.update({
    where: { id: reportId },
    data: { resolvedAt: new Date() },
  });
}

export async function getAdminStats() {
  const now = new Date();
  const startOfDay = new Date(now);
  startOfDay.setHours(0, 0, 0, 0);
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - 6);
  startOfWeek.setHours(0, 0, 0, 0);

  const [
    todayCount,
    weekCount,
    revenue,
    clients,
    barbers,
    availableBarbers,
    pending,
    pendingApplications,
    openReports,
    weekReservations,
  ] = await Promise.all([
    prisma.reservation.count({
      where: { createdAt: { gte: startOfDay } },
    }),
    prisma.reservation.count({
      where: { createdAt: { gte: startOfWeek } },
    }),
    prisma.reservation.aggregate({
      where: { status: "TERMINEE" },
      _sum: { total: true },
    }),
    prisma.user.count({ where: { role: "CLIENT" } }),
    prisma.barber.count(),
    prisma.barber.count({ where: { isAvailable: true } }),
    prisma.reservation.count({ where: { status: "DEMANDE_ENVOYEE" } }),
    prisma.barber.count({ where: { approvalStatus: "PENDING" } }),
    prisma.report.count({ where: { resolvedAt: null } }),
    prisma.reservation.findMany({
      where: { createdAt: { gte: startOfWeek } },
      select: { createdAt: true, total: true, status: true },
    }),
  ]);

  // Build a 7-day series for the chart.
  const days: { label: string; count: number; revenue: number }[] = [];
  const fmt = new Intl.DateTimeFormat("fr-BE", { weekday: "short" });
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    d.setHours(0, 0, 0, 0);
    const dayEnd = new Date(d);
    dayEnd.setHours(23, 59, 59, 999);
    const inDay = weekReservations.filter(
      (r) => r.createdAt >= d && r.createdAt <= dayEnd,
    );
    days.push({
      label: fmt.format(d),
      count: inDay.length,
      revenue: inDay
        .filter((r) => r.status === "TERMINEE")
        .reduce((sum, r) => sum + r.total, 0),
    });
  }

  return {
    todayCount,
    weekCount,
    revenue: revenue._sum.total ?? 0,
    clients,
    barbers,
    availableBarbers,
    pending,
    pendingApplications,
    openReports,
    series: days,
  };
}
