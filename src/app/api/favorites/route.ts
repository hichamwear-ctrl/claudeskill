import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ok, fail, handleError } from "@/server/api";

export async function GET() {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);
  const favorites = await prisma.favorite.findMany({
    where: { userId: session.user.id },
    include: { barber: { include: { user: true } } },
    orderBy: { createdAt: "desc" },
  });
  return ok({ favorites });
}

const schema = z.object({ barberId: z.string() });

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { barberId } = schema.parse(await req.json());
    const barber = await prisma.barber.findUnique({ where: { id: barberId } });
    if (!barber) return fail("Barber introuvable", 404);

    const favorite = await prisma.favorite.upsert({
      where: { userId_barberId: { userId: session.user.id, barberId } },
      update: {},
      create: { userId: session.user.id, barberId },
    });
    return ok({ favorite }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
