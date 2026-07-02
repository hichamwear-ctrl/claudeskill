import type { MissionListItem } from '@/features/missions';
import { callRpc, unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';
import type { MissionStatus } from '@/types/domain';

const LIST_COLUMNS = 'id,status,category_id,dropoff_address,estimated_price,quoted_price,final_amount,created_at';

/** Missions attribuées à l'intervenant courant (RLS). */
export async function fetchAssignedMissions(operatorId: string): Promise<MissionListItem[]> {
  return unwrap<MissionListItem[]>(
    supabase
      .from('missions')
      .select(LIST_COLUMNS)
      .eq('operator_id', operatorId)
      .order('created_at', { ascending: false }),
  );
}

/** Transition d'exécution (allow-list + rôle vérifiés côté base). */
export function transitionMission(missionId: string, to: MissionStatus, reason?: string): Promise<unknown> {
  return callRpc('transition_mission', { p_mission_id: missionId, p_to: to, p_reason: reason });
}
