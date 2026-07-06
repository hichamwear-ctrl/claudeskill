import { NextResponse } from "next/server";
import { ZodError } from "zod";
import { captureError } from "@/server/monitoring";

export function ok<T>(data: T, init?: ResponseInit) {
  return NextResponse.json({ data }, init);
}

export function fail(message: string, status = 400, extra?: unknown) {
  return NextResponse.json({ error: message, details: extra }, { status });
}

export function handleError(error: unknown) {
  if (error instanceof ZodError) {
    return fail("Données invalides", 422, error.flatten().fieldErrors);
  }
  // Domain errors carry a safe message + intended HTTP status (e.g. OrderError).
  if (
    error &&
    typeof error === "object" &&
    "status" in error &&
    typeof (error as { status: unknown }).status === "number" &&
    error instanceof Error
  ) {
    return fail(error.message, (error as { status: number }).status);
  }
  // Never leak internals to the client; report to the monitoring seam instead.
  captureError(error, { scope: "api" });
  return fail("Erreur serveur", 500);
}

/**
 * Minimal in-memory sliding-window rate limiter.
 * Sufficient for a single instance / dev. Swap for Redis in production.
 */
const buckets = new Map<string, { count: number; resetAt: number }>();

export function rateLimit(
  key: string,
  { limit = 10, windowMs = 60_000 } = {},
): { allowed: boolean; remaining: number } {
  const now = Date.now();
  const bucket = buckets.get(key);

  if (!bucket || bucket.resetAt < now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return { allowed: true, remaining: limit - 1 };
  }
  bucket.count += 1;
  return { allowed: bucket.count <= limit, remaining: Math.max(0, limit - bucket.count) };
}

export function clientKey(req: Request, scope: string): string {
  const fwd = req.headers.get("x-forwarded-for");
  const ip = fwd?.split(",")[0]?.trim() ?? "local";
  return `${scope}:${ip}`;
}
