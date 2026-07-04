import { auth } from "@/lib/auth";
import { createReservation, getClientDashboard } from "@/lib/reservations";
import { createReservationSchema } from "@/lib/validations";
import { ok, fail, handleError, rateLimit } from "@/lib/api";

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { allowed } = rateLimit(`reservation:${session.user.id}`, {
      limit: 20,
      windowMs: 60_000,
    });
    if (!allowed) return fail("Trop de requêtes", 429);

    const data = createReservationSchema.parse(await req.json());
    const reservation = await createReservation(session.user.id, data);
    return ok({ reservation }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    const dashboard = await getClientDashboard(session.user.id);
    return ok(dashboard);
  } catch (error) {
    return handleError(error);
  }
}
