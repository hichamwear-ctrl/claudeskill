import "server-only";
import type { CallProvider } from "./provider";
import { mockCallProvider } from "./mock";
import { createTwilioCallProvider } from "./twilio";

let cached: CallProvider | null = null;

/** Twilio when fully configured, otherwise the inline mock (demo) provider. */
export function getCallProvider(): CallProvider {
  if (cached) return cached;
  const {
    CALL_PROVIDER,
    TWILIO_ACCOUNT_SID,
    TWILIO_API_KEY,
    TWILIO_API_SECRET,
    TWILIO_TWIML_APP_SID,
  } = process.env;

  if (
    CALL_PROVIDER === "twilio" &&
    TWILIO_ACCOUNT_SID &&
    TWILIO_API_KEY &&
    TWILIO_API_SECRET
  ) {
    cached = createTwilioCallProvider({
      accountSid: TWILIO_ACCOUNT_SID,
      apiKey: TWILIO_API_KEY,
      apiSecret: TWILIO_API_SECRET,
      twimlAppSid: TWILIO_TWIML_APP_SID,
    });
  } else {
    cached = mockCallProvider;
  }
  return cached;
}

export type { CallProvider } from "./provider";
