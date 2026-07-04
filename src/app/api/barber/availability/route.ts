import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { ok, fail, handleError } from "@/server/api";

const schema = z.object({ isAvailable: z.boolean() });

export async function PATCH(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action non autorisée", 403);

    const { isAvailable } = schema.parse(await req.json());
    const barber = await ensureBarberProfile(session.user.id);
    const updated = await prisma.barber.update({
      where: { id: barber.id },
      data: { isAvailable },
    });
    return ok({ barber: updated });
  } catch (error) {
    return handleError(error);
  }
}
