import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { getOrderParticipant } from "@/server/orders";
import { notify } from "@/server/notifications";
import { publishMessage } from "@/server/realtime/publisher";
import { isConversationActive } from "@/lib/status";
import { messageSchema } from "@/lib/validations";
import { ok, fail, handleError, rateLimit } from "@/server/api";

/** List the messages of an order (both parties, chronological). */
export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { id } = await params;
    await getOrderParticipant(id, session.user.id, session.user.role === "ADMIN");

    const since = new URL(req.url).searchParams.get("since");
    const messages = await prisma.message.findMany({
      where: {
        reservationId: id,
        ...(since ? { createdAt: { gt: new Date(since) } } : {}),
      },
      orderBy: { createdAt: "asc" },
      take: 200,
      select: {
        id: true,
        senderId: true,
        body: true,
        createdAt: true,
      },
    });
    return ok({ messages });
  } catch (error) {
    return handleError(error);
  }
}

/** Send a message. Allowed only while the conversation window is open. */
export async function POST(
  req: Request,
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
      return fail("Le chat n'est pas ouvert pour cette réservation", 422);

    const { allowed } = rateLimit(`chat:${session.user.id}`, {
      limit: 30,
      windowMs: 60_000,
    });
    if (!allowed) return fail("Trop de messages, patientez.", 429);

    const { body } = messageSchema.parse(await req.json());
    const message = await prisma.message.create({
      data: { reservationId: id, senderId: session.user.id, body },
      select: { id: true, senderId: true, body: true, createdAt: true },
    });

    await publishMessage(id, message).catch(() => {});
    if (participant.otherUserId) {
      await notify(participant.otherUserId, {
        title: "Nouveau message",
        body: body.length > 80 ? `${body.slice(0, 80)}…` : body,
      });
    }
    return ok({ message }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
