import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { ok, fail, handleError } from "@/server/api";

/** Remove a photo from the barber's own portfolio. */
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action réservée aux barbers", 403);

    const { id } = await params;
    const barber = await ensureBarberProfile(session.user.id);
    const photo = await prisma.barberPhoto.findUnique({ where: { id } });
    if (!photo || photo.barberId !== barber.id)
      return fail("Photo introuvable", 404);

    await prisma.barberPhoto.delete({ where: { id } });
    return ok({ deleted: true });
  } catch (error) {
    return handleError(error);
  }
}
