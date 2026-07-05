import { z } from "zod";
import { auth } from "@/server/auth";
import { redeemLoyalty } from "@/server/loyalty";
import { ok, fail, handleError, rateLimit } from "@/server/api";

const schema = z.object({ euro: z.number().int().positive() });

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { allowed } = rateLimit(`redeem:${session.user.id}`, { limit: 10 });
    if (!allowed) return fail("Trop de requêtes", 429);

    const { euro } = schema.parse(await req.json());
    const code = await redeemLoyalty(session.user.id, euro);
    return ok({ code });
  } catch (error) {
    if (error instanceof Error && /invalide|insuffisant/i.test(error.message)) {
      return fail(error.message, 422);
    }
    return handleError(error);
  }
}
