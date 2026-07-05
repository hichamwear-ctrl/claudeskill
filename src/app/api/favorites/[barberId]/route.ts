import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ok, fail, handleError } from "@/server/api";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ barberId: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { barberId } = await params;
    await prisma.favorite.deleteMany({
      where: { userId: session.user.id, barberId },
    });
    return ok({ deleted: true });
  } catch (error) {
    return handleError(error);
  }
}
