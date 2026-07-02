import type { PostgrestError } from '@supabase/supabase-js';

import { mapPostgrestError } from '@/lib/errors';

/**
 * Exécute une requête PostgREST (soumise à la RLS) et lève un `AppError` en cas
 * d'échec. Les lectures passent par `supabase.from(...)` dans les features ;
 * ce helper normalise seulement `{ data, error }` → `data | throw`.
 */
export async function unwrap<T>(
  query: PromiseLike<{ data: T | null; error: PostgrestError | null }>,
): Promise<T> {
  const { data, error } = await query;
  if (error) throw mapPostgrestError(error);
  return data as T;
}
