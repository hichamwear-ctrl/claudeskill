import { callEdge, callRpc } from '@/services/api';

export interface ReviewQueueItem {
  mission_id: string;
  status: string;
  submitted_at: string | null;
  review_claimed_by: string | null;
  review_claimed_at: string | null;
  client_id: string;
  client_name: string | null;
  category_slug: string | null;
  category_label: string | null;
  summary: string | null;
}

export type ReviewActionKind = 'claim' | 'release' | 'accept' | 'reject' | 'need_info';

/** File de revue enrichie (RPC, filtrée par visibilité de claim). */
export async function fetchReviewQueue(): Promise<ReviewQueueItem[]> {
  const data = await callRpc('operator_queue', {});
  return data as unknown as ReviewQueueItem[];
}

/** Action de revue (claim/décision) via l'Edge `review`. */
export function reviewAction(input: {
  missionId: string;
  action: ReviewActionKind;
  reason?: string;
  price?: number;
  etaMin?: number;
}): Promise<unknown> {
  return callEdge('review', {
    mission_id: input.missionId,
    action: input.action,
    reason: input.reason,
    price: input.price,
    eta_min: input.etaMin,
  });
}
