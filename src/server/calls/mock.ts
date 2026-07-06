import type { CallProvider } from "./provider";

/**
 * Default provider: creates a deterministic room id and no token. The UI treats
 * a missing token as "demo mode" and simulates the audio session — enough to
 * exercise the full start/end lifecycle without any external service.
 */
export const mockCallProvider: CallProvider = {
  name: "mock",
  async createCall({ reservationId }) {
    return {
      room: `bh-${reservationId}-${Date.now().toString(36)}`,
      provider: "mock",
      note: "Appel en mode démo (aucun service tiers configuré).",
    };
  },
  async endCall() {
    /* nothing to tear down in mock mode */
  },
};
