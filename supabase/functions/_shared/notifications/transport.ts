/**
 * Interface de transport des notifications (M8) — le domaine ne connaît QUE ça.
 * Réf. NOTIFICATIONS.md §6/§12.
 *
 * Aujourd'hui : `MockExpoTransport`. Demain : Expo réel / FCM / APNS / Email /
 * SMS / Web Push — même interface, **aucun changement** du domaine (RPC) ni de
 * l'Edge. Sélection par configuration (`NOTIFY_TRANSPORT`).
 */
import { optionalEnv } from '../env.ts';

/** Une notification prête à être poussée (résolue en base). */
export interface PushMessage {
  notificationId: string;
  userId: string;
  title: string;
  body: string | null;
  deepLink: string | null;
  payload: Record<string, unknown>;
  tokens: string[];
}

export interface PushResult {
  notificationId: string;
  ok: boolean;
  delivered: number;
}

export interface PushTransport {
  readonly name: string;
  send(messages: PushMessage[]): Promise<PushResult[]>;
}

/** Transport simulé : aucun appel externe ; reproduit un envoi multi-jetons. */
export class MockExpoTransport implements PushTransport {
  readonly name = 'mock';
  send(messages: PushMessage[]): Promise<PushResult[]> {
    return Promise.resolve(
      messages.map((m) => ({
        notificationId: m.notificationId,
        ok: true,
        delivered: m.tokens.length,
      })),
    );
  }
}

/** Sélection du transport par configuration (défaut mock). */
export function getTransport(): PushTransport {
  const name = optionalEnv('NOTIFY_TRANSPORT', 'mock');
  switch (name) {
    case 'mock':
      return new MockExpoTransport();
    // case 'expo': return new ExpoTransport();   // futur — même interface
    // case 'fcm':  return new FcmTransport();
    default:
      throw new Error(`Transport de notification inconnu: ${name}`);
  }
}
