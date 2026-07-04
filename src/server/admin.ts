import { prisma } from "./prisma";

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
    series: days,
  };
}
