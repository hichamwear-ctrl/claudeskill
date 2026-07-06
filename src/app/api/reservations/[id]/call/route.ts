import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { getOrderParticipant } from "@/server/orders";
import { getCallProvider } from "@/server/calls";
import { notify } from "@/server/notifications";
import { publishCall } from "@/server/realtime/publisher";
import { isConversationActive } from "@/lib/status";
import { ok, fail, handleError } from "@/server/api";

/** Start an audio call. Available only while the conversation window is open. */
export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { id } = await params;
    const participant = await getOrderParticipant(
      id,
      session.user.id,
      session.user.role === "ADMIN",
    );
    if (!isConversationActive(participant.status))
      return fail("Les appels ne sont pas disponibles pour ce statut", 422);

    const provider = getCallProvider();
    const result = await provider.createCall({
      reservationId: id,
      initiatorId: session.user.id,
    });

    const call = await prisma.callSession.create({
      data: {
        reservationId: id,
        initiatorId: session.user.id,
        provider: result.provider,
        room: result.room,
        status: "INITIATED",
        startedAt: new Date(),
      },
    });

    await publishCall(id, {
      id: call.id,
      status: "INITIATED",
      initiatorId: session.user.id,
    }).catch(() => {});
    if (participant.otherUserId) {
      await notify(participant.otherUserId, {
        title: "Appel entrant",
        body: "Votre interlocuteur tente de vous appeler.",
      });
    }

    return ok({
      call: { id: call.id, room: result.room, provider: result.provider },
      token: result.token ?? null,
      note: result.note ?? null,
    });
  } catch (error) {
    return handleError(error);
  }
}

/** End an active call. */
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { id } = await params;
    await getOrderParticipant(id, session.user.id, session.user.role === "ADMIN");

    const { callId } = (await req.json().catch(() => ({}))) as { callId?: string };
    const call = callId
      ? await prisma.callSession.findFirst({ where: { id: callId, reservationId: id } })
      : await prisma.callSession.findFirst({
          where: { reservationId: id, status: { in: ["INITIATED", "ONGOING"] } },
          orderBy: { createdAt: "desc" },
        });
    if (!call) return fail("Appel introuvable", 404);

    const updated = await prisma.callSession.update({
      where: { id: call.id },
      data: { status: "ENDED", endedAt: new Date() },
    });
    if (updated.room) await getCallProvider().endCall(updated.room);
    await publishCall(id, {
      id: updated.id,
      status: "ENDED",
      initiatorId: updated.initiatorId,
    }).catch(() => {});

    return ok({ call: { id: updated.id, status: updated.status } });
  } catch (error) {
    return handleError(error);
  }
}
