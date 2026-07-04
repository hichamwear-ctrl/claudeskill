import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ok, fail, handleError } from "@/server/api";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { id } = await params;
    const address = await prisma.address.findFirst({
      where: { id, userId: session.user.id },
    });
    if (!address) return fail("Adresse introuvable", 404);

    await prisma.address.delete({ where: { id } });
    return ok({ deleted: true });
  } catch (error) {
    return handleError(error);
  }
}
