import { mapPostgrestError } from '@/lib/errors';
import { supabase } from '@/services/supabase/client';
import type { Database } from '@/types/database.types';

type FunctionName = keyof Database['public']['Functions'];
type ArgsOf<K extends FunctionName> = Database['public']['Functions'][K]['Args'];
type ReturnsOf<K extends FunctionName> = Database['public']['Functions'][K]['Returns'];

/**
 * Appelle une RPC Postgres (`SECURITY DEFINER`) typée. L'autorisation est
 * vérifiée côté base ; les erreurs SQLSTATE sont traduites en `AppError`
 * (mêmes codes que les Edge Functions).
 */
export async function callRpc<K extends FunctionName>(fn: K, args: ArgsOf<K>): Promise<ReturnsOf<K>> {
  const { data, error } = await supabase.rpc(fn, args as never);
  if (error) throw mapPostgrestError(error);
  return data as ReturnsOf<K>;
}
