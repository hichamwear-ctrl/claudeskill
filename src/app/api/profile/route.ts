import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ok, fail, handleError } from "@/server/api";

// Accept either a hosted URL or an inline data: URL (uploaded photo). Capped to
// ~4 MB of base64 to keep the payload and column size reasonable.
const imageField = z
  .string()
  .max(5_600_000)
  .refine(
    (v) => /^https?:\/\//.test(v) || /^data:image\/[a-z+]+;base64,/.test(v),
    "Image invalide",
  );

const profileSchema = z.object({
  firstName: z.string().min(2),
  lastName: z.string().min(2),
  username: z.string().min(3).optional().or(z.literal("")),
  phone: z.string().optional().or(z.literal("")),
  image: imageField.optional().or(z.literal("")),
});

export async function PATCH(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const data = profileSchema.parse(await req.json());

    if (data.username) {
      const taken = await prisma.user.findFirst({
        where: { username: data.username, NOT: { id: session.user.id } },
      });
      if (taken) return fail("Ce pseudo est déjà pris", 409);
    }

    const user = await prisma.user.update({
      where: { id: session.user.id },
      data: {
        firstName: data.firstName,
        lastName: data.lastName,
        username: data.username || null,
        phone: data.phone || null,
        image: data.image || null,
      },
      select: { id: true, firstName: true, lastName: true },
    });
    return ok({ user });
  } catch (error) {
    return handleError(error);
  }
}
