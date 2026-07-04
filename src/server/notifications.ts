import type { NotificationChannel, ReservationStatus } from "@prisma/client";
import { prisma } from "./prisma";
import { STATUS_META } from "@/lib/status";

interface NotifyInput {
  channel?: NotificationChannel;
  title: string;
  body: string;
}

/**
 * Central notification dispatcher.
 * Persists an in-app notification and dispatches to external channels.
 * Email/SMS providers (Resend, Twilio, …) plug in here later.
 */
export async function notify(userId: string, input: NotifyInput) {
  const channel = input.channel ?? "REALTIME";

  const notification = await prisma.notification.create({
    data: { userId, channel, title: input.title, body: input.body },
  });

  switch (channel) {
    case "EMAIL":
      // await sendEmail(...)
      break;
    case "SMS":
      // await sendSms(...)
      break;
    case "REALTIME":
      // await pusher/socket broadcast(...)
      break;
  }

  return notification;
}

/** Notifies the client when a reservation status changes. */
export async function notifyStatusChange(
  clientId: string,
  reference: string,
  status: ReservationStatus,
) {
  const meta = STATUS_META[status];
  return notify(clientId, {
    channel: "REALTIME",
    title: `Réservation ${reference.slice(0, 6).toUpperCase()} — ${meta.label}`,
    body: meta.description,
  });
}
