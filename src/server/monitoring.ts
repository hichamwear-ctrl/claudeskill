import "server-only";
import { logger } from "@/lib/logger";

/**
 * Error monitoring seam (Phase 4). Inert by default; wire Sentry by installing
 * `@sentry/nextjs`, setting `SENTRY_DSN`, and forwarding in `captureError`
 * (see docs/DEPLOYMENT.md → Monitoring). Nothing else in the app changes.
 */
export function captureError(error: unknown, context?: Record<string, unknown>) {
  logger.error("captured error", { error: serialize(error), ...context });

  if (process.env.SENTRY_DSN) {
    // Integration point:
    // import * as Sentry from "@sentry/nextjs";
    // Sentry.captureException(error, { extra: context });
  }
}

function serialize(error: unknown) {
  if (error instanceof Error) {
    return { name: error.name, message: error.message, stack: error.stack };
  }
  return error;
}
