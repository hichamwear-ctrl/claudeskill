import { auth } from "@/server/auth";
import { acceptRequest } from "@/server/orders";
import { ok, fail, handleError } from "@/server/api";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "BARBER" && session.user.role !== "ADMIN")
      return fail("Action réservée aux barbers", 403);

    const { id } = await params;
    const reservation = await acceptRequest(id, session.user.id);
    return ok({ reservation });
  } catch (error) {
    return handleError(error);
  }
}
