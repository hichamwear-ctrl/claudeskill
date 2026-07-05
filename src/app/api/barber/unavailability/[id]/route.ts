import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { ok, fail, handleError } from "@/server/api";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action non autorisée", 403);

    const { id } = await params;
    const barber = await ensureBarberProfile(session.user.id);
    await prisma.unavailability.deleteMany({
      where: { id, barberId: barber.id },
    });
    return ok({ deleted: true });
  } catch (error) {
    return handleError(error);
  }
}
