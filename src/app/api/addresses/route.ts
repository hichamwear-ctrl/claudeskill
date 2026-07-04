import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { addressSchema } from "@/lib/validations";
import { resolveZone } from "@/lib/zones";
import { ok, fail, handleError } from "@/lib/api";

export async function GET() {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);
  const addresses = await prisma.address.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
  });
  return ok({ addresses });
}

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const data = addressSchema.parse(await req.json());
    const { insideZone } = resolveZone({
      postalCode: data.postalCode,
      latitude: data.latitude,
      longitude: data.longitude,
    });

    const count = await prisma.address.count({
      where: { userId: session.user.id },
    });

    const address = await prisma.address.create({
      data: {
        userId: session.user.id,
        label: data.label,
        street: data.street,
        number: data.number || null,
        city: data.city,
        postalCode: data.postalCode,
        country: data.country,
        latitude: data.latitude ?? null,
        longitude: data.longitude ?? null,
        insideZone,
        isDefault: count === 0,
      },
    });
    return ok({ address }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
