import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { ensureBarberProfile } from "@/server/barber";
import { barberProfileSchema } from "@/lib/validations";
import { ok, fail, handleError } from "@/server/api";

/** A barber edits their public profile (bio, seniority, socials). */
export async function PATCH(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action réservée aux barbers", 403);

    const data = barberProfileSchema.parse(await req.json());
    const barber = await ensureBarberProfile(session.user.id);

    const updated = await prisma.barber.update({
      where: { id: barber.id },
      data: {
        ...(data.bio !== undefined && { bio: data.bio || null }),
        ...(data.yearsExperience !== undefined && {
          yearsExperience: data.yearsExperience,
        }),
        ...(data.level !== undefined && { level: data.level }),
        ...(data.instagram !== undefined && { instagram: data.instagram || null }),
        ...(data.snapchat !== undefined && { snapchat: data.snapchat || null }),
      },
      select: { id: true, bio: true, level: true, yearsExperience: true },
    });
    return ok({ barber: updated });
  } catch (error) {
    return handleError(error);
  }
}
