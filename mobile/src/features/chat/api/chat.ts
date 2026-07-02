import { callRpc, unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';
import type { Message } from '@/types/domain';

/** Messages d'une mission (ordre chronologique). RLS : participants uniquement. */
export async function fetchMessages(missionId: string): Promise<Message[]> {
  return unwrap<Message[]>(
    supabase.from('messages').select('*').eq('mission_id', missionId).order('created_at', { ascending: true }),
  );
}

/** Envoi = INSERT (gardé par la RLS + trigger de modération côté base). */
export async function sendMessage(input: { missionId: string; senderId: string; body: string }): Promise<Message> {
  return unwrap<Message>(
    supabase
      .from('messages')
      .insert({ mission_id: input.missionId, sender_id: input.senderId, body: input.body })
      .select('*')
      .single(),
  );
}

/** Accusés de lecture (RPC). */
export function markMessagesRead(missionId: string): Promise<number> {
  return callRpc('mark_messages_read', { p_mission_id: missionId });
}
