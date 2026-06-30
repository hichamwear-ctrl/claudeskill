/**
 * Journalisation structurée (JSON sur une ligne) pour une exploitation facile
 * des logs Supabase. Chaque entrée porte le nom de la fonction et un requestId
 * de corrélation.
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface Logger {
  debug(message: string, meta?: Record<string, unknown>): void;
  info(message: string, meta?: Record<string, unknown>): void;
  warn(message: string, meta?: Record<string, unknown>): void;
  error(message: string, meta?: Record<string, unknown>): void;
}

export function createLogger(fn: string, requestId: string): Logger {
  const emit = (level: LogLevel, message: string, meta?: Record<string, unknown>) => {
    const line = {
      ts: new Date().toISOString(),
      level,
      fn,
      requestId,
      message,
      ...(meta ?? {}),
    };
    // console.error pour warn/error -> séparation des flux dans les logs.
    const sink = level === 'warn' || level === 'error' ? console.error : console.log;
    sink(JSON.stringify(line));
  };

  return {
    debug: (m, meta) => emit('debug', m, meta),
    info: (m, meta) => emit('info', m, meta),
    warn: (m, meta) => emit('warn', m, meta),
    error: (m, meta) => emit('error', m, meta),
  };
}
