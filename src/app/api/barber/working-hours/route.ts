import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { ok, fail, handleError } from "@/server/api";

const time = z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/, "Heure invalide");
const schema = z.object({
  hours: z
    .array(
      z.object({
        weekday: z.number().int().min(0).max(6),
        startTime: time,
        endTime: time,
        enabled: z.boolean(),
      }),
    )
    .max(7),
});

export async function GET() {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);
  if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
    return fail("Action non autorisée", 403);

  const barber = await ensureBarberProfile(session.user.id);
  const hours = await prisma.workingHours.findMany({
    where: { barberId: barber.id },
    orderBy: { weekday: "asc" },
  });
  return ok({ hours });
}

export async function PUT(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action non autorisée", 403);

    const { hours } = schema.parse(await req.json());
    const barber = await ensureBarberProfile(session.user.id);

    // Validate each range and upsert per weekday.
    for (const h of hours) {
      if (h.enabled && h.startTime >= h.endTime)
        return fail(`Plage invalide pour le jour ${h.weekday}`, 422);
      await prisma.workingHours.upsert({
        where: { barberId_weekday: { barberId: barber.id, weekday: h.weekday } },
        update: { startTime: h.startTime, endTime: h.endTime, enabled: h.enabled },
        create: {
          barberId: barber.id,
          weekday: h.weekday,
          startTime: h.startTime,
          endTime: h.endTime,
          enabled: h.enabled,
        },
      });
    }
    const updated = await prisma.workingHours.findMany({
      where: { barberId: barber.id },
      orderBy: { weekday: "asc" },
    });
    return ok({ hours: updated });
  } catch (error) {
    return handleError(error);
  }
}
