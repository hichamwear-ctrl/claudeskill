import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { isValidUnavailability } from "@/lib/unavailability";
import { ok, fail, handleError } from "@/server/api";

const time = z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/);
const schema = z.object({
  date: z.string().min(1),
  allDay: z.boolean().default(true),
  startTime: time.optional(),
  endTime: time.optional(),
  type: z.enum(["BREAK", "LEAVE", "OFF"]).default("OFF"),
  reason: z.string().max(200).optional(),
});

export async function GET() {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);
  if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
    return fail("Action non autorisée", 403);

  const barber = await ensureBarberProfile(session.user.id);
  const items = await prisma.unavailability.findMany({
    where: { barberId: barber.id, date: { gte: new Date(new Date().setHours(0, 0, 0, 0)) } },
    orderBy: { date: "asc" },
  });
  return ok({ items });
}

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action non autorisée", 403);

    const data = schema.parse(await req.json());
    if (!isValidUnavailability(data))
      return fail("Plage horaire invalide", 422);

    const barber = await ensureBarberProfile(session.user.id);
    const item = await prisma.unavailability.create({
      data: {
        barberId: barber.id,
        date: new Date(data.date),
        allDay: data.allDay,
        startTime: data.allDay ? null : data.startTime,
        endTime: data.allDay ? null : data.endTime,
        type: data.type,
        reason: data.reason,
      },
    });
    return ok({ item }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
