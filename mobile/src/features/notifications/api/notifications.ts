import { callRpc, unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';
import type { Notification } from '@/types/domain';

/** Notifications in-app du destinataire courant (RLS). */
export async function fetchNotifications(): Promise<Notification[]> {
  return unwrap<Notification[]>(
    supabase.from('notifications').select('*').order('created_at', { ascending: false }).limit(50),
  );
}

export function markNotificationRead(id: string): Promise<undefined> {
  return callRpc('mark_notification_read', { p_id: id });
}

export function markAllNotificationsRead(): Promise<number> {
  return callRpc('mark_all_notifications_read', {});
}
