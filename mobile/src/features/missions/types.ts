import type { Json } from '@/types/database.types';
import type { MissionStatus, PaymentStatus } from '@/types/domain';

/** Ligne de liste des missions du client. */
export interface MissionListItem {
  id: string;
  status: MissionStatus;
  category_id: string | null;
  dropoff_address: string | null;
  estimated_price: number | null;
  quoted_price: number | null;
  final_amount: number | null;
  created_at: string;
}

export interface MissionEvent {
  id: string;
  from_status: MissionStatus | null;
  to_status: MissionStatus | null;
  reason: string | null;
  created_at: string;
}

export interface PaymentInfo {
  id: string;
  status: PaymentStatus;
  amount_authorized: number | null;
  amount_captured: number | null;
  currency: string;
}

/** Retour consolidé de la RPC `mission_overview`. */
export interface MissionOverview {
  mission: {
    id: string;
    status: MissionStatus;
    client_id: string;
    operator_id: string | null;
    category_id: string | null;
    dropoff_address: string | null;
    details: Json;
    quoted_price: number | null;
    final_amount: number | null;
    review_reason: string | null;
    submitted_at: string | null;
    accepted_at: string | null;
    completed_at: string | null;
    created_at: string;
  };
  payment: PaymentInfo | null;
  events: MissionEvent[];
  conversation: { id: string; status: string } | null;
  unread_messages: number;
}
