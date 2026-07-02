import { callEdge } from '@/services/api';

import type { AnswerValue, Dossier, PriceEstimate, TurnResult, ZoneCheckResult } from '../types';

export interface ConverseInput {
  conversation_id?: string;
  message?: string;
  answer?: { key: string; value: AnswerValue };
  locale?: string;
}

/** Un tour de dialogue (crée la conversation si `conversation_id` absent). */
export function converse(input: ConverseInput): Promise<TurnResult> {
  return callEdge<TurnResult, ConverseInput>('converse', input);
}

/** Clôture de l'intake → mission `pending_review` (idempotent par conversation). */
export function submitRequest(conversationId: string): Promise<Dossier> {
  return callEdge<Dossier>(
    'submit-request',
    { conversation_id: conversationId },
    { idempotencyKey: `submit:${conversationId}` },
  );
}

export interface Coordinates {
  lat: number;
  lng: number;
}

/** Couverture géographique + horaires pour une position. */
export function zoneCheck(input: Coordinates & { at?: string }): Promise<ZoneCheckResult> {
  return callEdge<ZoneCheckResult>('zone-check', input);
}

/** Estimation prix + ETA (aucun effet de bord). */
export function estimatePrice(input: {
  category_id: string;
  dropoff: Coordinates;
  pickup?: Coordinates;
}): Promise<PriceEstimate> {
  return callEdge<PriceEstimate>('estimate-price', input);
}
