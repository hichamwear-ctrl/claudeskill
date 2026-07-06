import { auth } from "@/server/auth";
import { moderateBarber } from "@/server/admin";
import { notify } from "@/server/notifications";
import { prisma } from "@/server/prisma";
import { barberModerationSchema } from "@/lib/validations";
import { ok, fail, handleError } from "@/server/api";

/** Admin moderation: approve/refuse applications, ban/suspend/delete barbers. */
export async function PATCH(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role !== "ADMIN") return fail("Réservé à l'administrateur", 403);

    const { barberId, action } = barberModerationSchema.parse(await req.json());

    // Capture the account owner before a possible delete for the notification.
    const barber = await prisma.barber.findUnique({
      where: { id: barberId },
      select: { userId: true },
    });

    await moderateBarber(barberId, action);

    if (barber && action !== "DELETE") {
      const messages: Record<string, string> = {
        APPROVE: "Votre compte barber a été validé. Vous pouvez vous connecter.",
        REFUSE: "Votre demande de compte barber a été refusée.",
        BAN: "Votre compte a été banni.",
        UNBAN: "Votre compte a été réactivé.",
        SUSPEND: "Votre compte a été suspendu.",
        UNSUSPEND: "Votre suspension a été levée.",
      };
      if (messages[action]) {
        await notify(barber.userId, {
          title: "Mise à jour de votre compte",
          body: messages[action],
        });
      }
    }

    return ok({ done: true });
  } catch (error) {
    return handleError(error);
  }
}
