import { env } from '@/constants/env';
import { AppError, normalizeErrorCode } from '@/lib/errors';
import { supabase } from '@/services/supabase/client';

/** Edge Functions consommées par le mobile (`send-push` est interne au serveur). */
export type EdgeFunctionName =
  | 'health'
  | 'converse'
  | 'submit-request'
  | 'review'
  | 'estimate-price'
  | 'zone-check'
  | 'payments';

export interface CallEdgeOptions {
  method?: 'GET' | 'POST';
  /** En-tête `Idempotency-Key` pour les mutations sensibles (paiement, transitions à effet). */
  idempotencyKey?: string;
  signal?: AbortSignal;
}

interface EdgeErrorBody {
  error?: { message?: string; code?: string };
}

/**
 * Appelle une Edge Function et **déballe l'enveloppe** `{ data } | { error }`.
 * - succès → renvoie `data` typé `TOut`.
 * - erreur → lève un `AppError` (code stable + message).
 * Ajoute systématiquement `Authorization` (si session), `apikey`, `X-Api-Version`.
 */
export async function callEdge<TOut, TIn = unknown>(
  fn: EdgeFunctionName,
  body?: TIn,
  opts: CallEdgeOptions = {},
): Promise<TOut> {
  const method = opts.method ?? 'POST';
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    apikey: env.supabaseAnonKey,
    'X-Api-Version': env.apiVersion,
  };
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey;

  let res: Response;
  try {
    res = await fetch(`${env.supabaseUrl}/functions/v1/${fn}`, {
      method,
      headers,
      body: method === 'GET' || body === undefined ? undefined : JSON.stringify(body),
      signal: opts.signal,
    });
  } catch {
    throw new AppError('network_error', 'Connexion perdue.', 0);
  }

  const text = await res.text();
  let json: unknown = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      json = null; // réponse non-JSON : on retombe sur le statut HTTP
    }
  }

  if (!res.ok) {
    const err = (json as EdgeErrorBody | null)?.error;
    throw new AppError(
      normalizeErrorCode(err?.code, res.status),
      err?.message ?? 'Erreur serveur',
      res.status,
    );
  }

  return (json as { data: TOut } | null)?.data as TOut;
}
