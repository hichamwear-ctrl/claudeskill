/**
 * Minimal structured logger (Phase 4). Level via `LOG_LEVEL`
 * (debug|info|warn|error), default "info". Isomorphic and dependency-free.
 */
type Level = "debug" | "info" | "warn" | "error";
const ORDER: Record<Level, number> = { debug: 0, info: 1, warn: 2, error: 3 };

function threshold(): number {
  const env = (process.env.LOG_LEVEL as Level) || "info";
  return ORDER[env] ?? ORDER.info;
}

function emit(level: Level, msg: string, meta?: unknown) {
  if (ORDER[level] < threshold()) return;
  const line = `[${new Date().toISOString()}] ${level.toUpperCase()} ${msg}`;
  const fn = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
  if (meta === undefined) fn(line);
  else fn(line, meta);
}

export const logger = {
  debug: (m: string, meta?: unknown) => emit("debug", m, meta),
  info: (m: string, meta?: unknown) => emit("info", m, meta),
  warn: (m: string, meta?: unknown) => emit("warn", m, meta),
  error: (m: string, meta?: unknown) => emit("error", m, meta),
};
