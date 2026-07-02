import { callRpc, unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';

import type { MissionListItem, MissionOverview } from '../types';

const LIST_COLUMNS = 'id,status,category_id,dropoff_address,estimated_price,quoted_price,final_amount,created_at';

/** Missions du client courant (RLS : ne voit que les siennes). */
export async function fetchMyMissions(clientId: string): Promise<MissionListItem[]> {
  return unwrap<MissionListItem[]>(
    supabase
      .from('missions')
      .select(LIST_COLUMNS)
      .eq('client_id', clientId)
      .order('created_at', { ascending: false }),
  );
}

/** Détail consolidé (mission + paiement + événements + conversation + non-lus). */
export async function fetchMissionOverview(missionId: string): Promise<MissionOverview> {
  const data = await callRpc('mission_overview', { p_mission_id: missionId });
  return data as unknown as MissionOverview;
}
