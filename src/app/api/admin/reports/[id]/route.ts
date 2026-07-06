import { auth } from "@/server/auth";
import { resolveReport } from "@/server/admin";
import { ok, fail, handleError } from "@/server/api";

/** Admin marks a report as resolved. */
export async function PATCH(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "ADMIN") return fail("Réservé à l'administrateur", 403);

    const { id } = await params;
    const report = await resolveReport(id);
    return ok({ report });
  } catch (error) {
    return handleError(error);
  }
}
