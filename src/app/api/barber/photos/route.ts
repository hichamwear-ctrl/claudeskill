import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { barberPhotoSchema } from "@/lib/validations";
import { ok, fail, handleError } from "@/server/api";

/** Add a photo to the barber's portfolio. */
export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action réservée aux barbers", 403);

    const { url, caption } = barberPhotoSchema.parse(await req.json());
    const barber = await ensureBarberProfile(session.user.id);

    const count = await prisma.barberPhoto.count({ where: { barberId: barber.id } });
    if (count >= 12) return fail("Limite de 12 photos atteinte", 422);

    const photo = await prisma.barberPhoto.create({
      data: { barberId: barber.id, url, caption: caption || null },
    });
    return ok({ photo }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
