/**
 * SMS provider abstraction (Phase 3). Swap the dev logger for Twilio / Vonage
 * by implementing `SmsProvider`.
 */
import "server-only";

export interface SmsMessage {
  to: string;
  text: string;
}

export interface SmsProvider {
  readonly name: string;
  send(message: SmsMessage): Promise<void>;
}

export const consoleSmsProvider: SmsProvider = {
  name: "console",
  async send(message) {
    if (process.env.NODE_ENV !== "test") {
      console.info(`[sms:console] → ${message.to} — ${message.text}`);
    }
  },
};

let provider: SmsProvider = consoleSmsProvider;
export function setSmsProvider(p: SmsProvider) {
  provider = p;
}
export function getSmsProvider(): SmsProvider {
  return provider;
}
