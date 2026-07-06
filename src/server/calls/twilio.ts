import type { CallProvider } from "./provider";

/**
 * Twilio Voice adapter (Phase 5).
 *
 * This is the integration seam. Wiring the real Twilio Programmable Voice SDK
 * is a deployment step: install `twilio`, then mint an AccessToken with a
 * VoiceGrant here and hand it to the browser Voice SDK. We build the room name
 * and surface the configured identity without pulling the SDK into the bundle,
 * so the project stays buildable until credentials are provisioned.
 */
export function createTwilioCallProvider(config: {
  accountSid: string;
  apiKey: string;
  apiSecret: string;
  twimlAppSid?: string;
}): CallProvider {
  return {
    name: "twilio",
    async createCall({ reservationId, initiatorId }) {
      const room = `bh-${reservationId}`;
      // Real implementation:
      //   const token = new AccessToken(accountSid, apiKey, apiSecret, { identity: initiatorId });
      //   token.addGrant(new VoiceGrant({ outgoingApplicationSid: twimlAppSid, incomingAllow: true }));
      //   return { room, token: token.toJwt(), provider: "twilio" };
      void config;
      void initiatorId;
      return {
        room,
        provider: "twilio",
        note: "Twilio configuré — génération du token à finaliser côté déploiement.",
      };
    },
    async endCall() {
      /* Twilio conferences end when both participants disconnect. */
    },
  };
}
