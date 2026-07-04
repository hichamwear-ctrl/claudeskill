import { prisma } from "@/server/prisma";
import { forgotPasswordSchema } from "@/lib/validations";
import { ok, handleError, rateLimit, clientKey } from "@/server/api";
import { notify } from "@/server/notifications";

export async function POST(req: Request) {
  try {
    const { allowed } = rateLimit(clientKey(req, "forgot"), { limit: 5 });
    if (!allowed) return ok({ sent: true }); // do not reveal rate-limit state

    const { email } = forgotPasswordSchema.parse(await req.json());
    const user = await prisma.user.findUnique({ where: { email } });

    if (user) {
      // In production: generate a signed token + email a reset link.
      await notify(user.id, {
        channel: "EMAIL",
        title: "Réinitialisation du mot de passe",
        body: "Cliquez sur le lien pour réinitialiser votre mot de passe.",
      });
    }

    // Constant response regardless of account existence.
    return ok({ sent: true });
  } catch (error) {
    return handleError(error);
  }
}
