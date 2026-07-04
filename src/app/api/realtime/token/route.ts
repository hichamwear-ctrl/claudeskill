import { auth } from "@/server/auth";
import { reservationChannel } from "@/lib/realtime";
import {
  authorizeReservationChannel,
  signChannelToken,
} from "@/server/realtime/auth";
import { ok, fail, handleError } from "@/server/api";

/**
 * Issues a short-lived signed token authorizing the current user to join a
 * reservation channel — only if they are its client, its barber, or an admin.
 */
export async function GET(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const reservationId = new URL(req.url).searchParams.get("reservationId");
    if (!reservationId) return fail("reservationId requis", 400);

    const allowed = await authorizeReservationChannel(
      { userId: session.user.id, role: session.user.role },
      reservationId,
    );
    if (!allowed) return fail("Accès au canal refusé", 403);

    const channel = reservationChannel(reservationId);
    const token = signChannelToken({ channel, userId: session.user.id });
    return ok({ channel, token });
  } catch (error) {
    return handleError(error);
  }
}
