/**
 * Email provider abstraction (Phase 3). Swap the dev logger for Resend /
 * SendGrid / SES by implementing `EmailProvider` — nothing else changes.
 */
import "server-only";

export interface EmailMessage {
  to: string;
  subject: string;
  html: string;
  text: string;
}

export interface EmailProvider {
  readonly name: string;
  send(message: EmailMessage): Promise<void>;
}

/** Default: logs instead of sending. Zero external dependency. */
export const consoleEmailProvider: EmailProvider = {
  name: "console",
  async send(message) {
    if (process.env.NODE_ENV !== "test") {
      console.info(`[email:console] → ${message.to} — ${message.subject}`);
    }
  },
};

let provider: EmailProvider = consoleEmailProvider;
export function setEmailProvider(p: EmailProvider) {
  provider = p;
}
export function getEmailProvider(): EmailProvider {
  return provider;
}
