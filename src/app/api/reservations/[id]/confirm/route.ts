import { auth } from "@/server/auth";
import { decideBarber } from "@/server/orders";
import { confirmBarberSchema } from "@/lib/validations";
import { ok, fail, handleError } from "@/server/api";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "CLIENT" && session.user.role !== "ADMIN")
      return fail("Action réservée au client", 403);

    const { id } = await params;
    const { decision } = confirmBarberSchema.parse(await req.json());
    const reservation = await decideBarber(id, session.user.id, decision);
    return ok({ reservation });
  } catch (error) {
    return handleError(error);
  }
}
