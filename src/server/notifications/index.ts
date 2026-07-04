/**
 * Central notification dispatcher (Phase 3).
 * Persists an in-app record and fans out to the active channel providers
 * (realtime broadcast, email, SMS) — all swappable, none duplicated.
 */
import "server-only";
import type { NotificationChannel, ReservationStatus } from "@prisma/client";
import { prisma } from "@/server/prisma";
import { publishReservationStatus } from "@/server/realtime/publisher";
import { renderStatusNotification } from "./templates";
import { getEmailProvider } from "./email";
import { getSmsProvider } from "./sms";

async function safe(label: string, fn: () => Promise<unknown>) {
  try {
    await fn();
  } catch (err) {
    console.error(`[notify] ${label} failed:`, err);
  }
}

interface NotifyInput {
  channel?: NotificationChannel;
  title: string;
  body: string;
}

/** Generic notification (used e.g. by password reset). */
export async function notify(userId: string, input: NotifyInput) {
  const channel = input.channel ?? "REALTIME";
  const notification = await prisma.notification.create({
    data: { userId, channel, title: input.title, body: input.body },
  });

  if (channel === "EMAIL" || channel === "SMS") {
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { email: true, phone: true },
    });
    if (channel === "EMAIL" && user?.email) {
      await safe("email", () =>
        getEmailProvider().send({
          to: user.email,
          subject: input.title,
          html: `<p>${input.body}</p>`,
          text: input.body,
        }),
      );
    }
    if (channel === "SMS" && user?.phone) {
      await safe("sms", () =>
        getSmsProvider().send({ to: user.phone!, text: `${input.title} — ${input.body}` }),
      );
    }
  }
  return notification;
}

export interface ReservationRef {
  id: string;
  clientId: string;
  reference: string;
}

/**
 * Fans a reservation status change out across every channel:
 * in-app record + live broadcast + email + SMS (best-effort).
 */
export async function notifyStatusChange(
  reservation: ReservationRef,
  status: ReservationStatus,
) {
  const t = renderStatusNotification(status, reservation.reference);

  await prisma.notification.create({
    data: {
      userId: reservation.clientId,
      channel: "REALTIME",
      title: t.title,
      body: t.body,
    },
  });

  await safe("realtime", () => publishReservationStatus(reservation.id, status));

  const client = await prisma.user.findUnique({
    where: { id: reservation.clientId },
    select: { email: true, phone: true },
  });
  if (client?.email) {
    await safe("email", () => getEmailProvider().send({ to: client.email, ...t.email }));
  }
  if (client?.phone) {
    await safe("sms", () => getSmsProvider().send({ to: client.phone!, text: t.sms.text }));
  }
}
