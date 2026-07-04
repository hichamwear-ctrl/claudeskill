import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";
import { registerSchema } from "@/lib/validations";
import { ok, fail, handleError, rateLimit, clientKey } from "@/lib/api";

export async function POST(req: Request) {
  try {
    const { allowed } = rateLimit(clientKey(req, "register"), {
      limit: 5,
      windowMs: 60_000,
    });
    if (!allowed) return fail("Trop de tentatives, réessayez plus tard.", 429);

    const body = await req.json();
    const data = registerSchema.parse(body);

    const existing = await prisma.user.findUnique({
      where: { email: data.email },
    });
    if (existing) return fail("Un compte existe déjà avec cet email.", 409);

    if (data.username) {
      const takenUsername = await prisma.user.findUnique({
        where: { username: data.username },
      });
      if (takenUsername) return fail("Ce pseudo est déjà pris.", 409);
    }

    const passwordHash = await bcrypt.hash(data.password, 12);

    const user = await prisma.user.create({
      data: {
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName,
        username: data.username || null,
        phone: data.phone || null,
        passwordHash,
        role: "CLIENT",
      },
      select: { id: true, email: true, firstName: true },
    });

    return ok({ user }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
