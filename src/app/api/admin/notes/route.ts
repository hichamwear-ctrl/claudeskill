import { auth } from "@/server/auth";
import { addAdminNote } from "@/server/admin";
import { adminNoteSchema } from "@/lib/validations";
import { ok, fail, handleError } from "@/server/api";

/** Admin attaches a private note to a barber. */
export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "ADMIN") return fail("Réservé à l'administrateur", 403);

    const { barberId, body } = adminNoteSchema.parse(await req.json());
    const note = await addAdminNote(barberId, session.user.id, body);
    return ok({ note }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
