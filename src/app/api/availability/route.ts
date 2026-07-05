import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { availableHourStarts, buildHourSlots } from "@/lib/slots";
import { ok, fail, handleError } from "@/server/api";

/**
 * Returns the bookable hour ranges for a date, derived from the working hours
 * of every available barber (minus their all-day unavailabilities). If no
 * barber covers an hour, that hour is simply not offered.
 */
export async function GET(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const dateStr = new URL(req.url).searchParams.get("date");
    if (!dateStr) return fail("date requise", 400);

    const date = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(date.getTime())) return fail("date invalide", 400);

    const weekday = date.getDay();
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);

    const workingHours = await prisma.workingHours.findMany({
      where: { weekday, enabled: true, barber: { isAvailable: true } },
      include: {
        barber: {
          include: {
            unavailabilities: { where: { date: { gte: date, lte: dayEnd } } },
          },
        },
      },
    });

    // Drop barbers who are entirely off that day.
    const ranges = workingHours
      .filter((h) => !h.barber.unavailabilities.some((u) => u.allDay))
      .map((h) => ({ startTime: h.startTime, endTime: h.endTime }));

    const slots = buildHourSlots(dateStr, availableHourStarts(ranges));
    return ok({ slots });
  } catch (error) {
    return handleError(error);
  }
}
