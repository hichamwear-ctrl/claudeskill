/**
 * Notification templates (Phase 3) — pure & unit-tested.
 * One source of truth for the copy sent across every channel (in-app, email,
 * SMS). Reuses the status metadata so wording stays consistent with the UI.
 */
import type { ReservationStatus } from "@prisma/client";
import { STATUS_META } from "@/lib/status";

export interface RenderedNotification {
  title: string;
  body: string;
  email: { subject: string; html: string; text: string };
  sms: { text: string };
}

function ref(reference: string): string {
  return reference.slice(0, 6).toUpperCase();
}

export function renderStatusNotification(
  status: ReservationStatus,
  reference: string,
): RenderedNotification {
  const meta = STATUS_META[status];
  const r = ref(reference);
  const title = `Réservation ${r} — ${meta.label}`;
  const body = meta.description;

  return {
    title,
    body,
    email: {
      subject: `[Barber Home] ${meta.label} — réservation ${r}`,
      text: `${title}\n\n${body}\n\n— Barber Home`,
      html: `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto">
  <h2 style="color:#B8942A;margin:0 0 8px">Barber Home</h2>
  <p style="font-size:16px;font-weight:600;margin:16px 0 4px">${meta.label}</p>
  <p style="color:#555;margin:0">${body}</p>
  <p style="color:#888;font-size:13px;margin-top:24px">Réservation ${r}</p>
</div>`,
    },
    sms: { text: `Barber Home — ${meta.label}. ${body} (réf. ${r})` },
  };
}
