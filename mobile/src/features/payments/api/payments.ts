import { callEdge } from '@/services/api';

/** Autorisation (client) — gate P1 en base : refusée si mission ≠ accepted. */
export function authorizePayment(missionId: string): Promise<unknown> {
  return callEdge(
    'payments',
    { mission_id: missionId, action: 'authorize' },
    { idempotencyKey: `pay-auth:${missionId}` },
  );
}

/** Capture (opérateur/admin) — preuve obligatoire ; montant plafonné en base. */
export function capturePayment(input: {
  missionId: string;
  proofPath: string;
  amountFinal?: number;
  advanceActual?: number;
}): Promise<unknown> {
  return callEdge(
    'payments',
    {
      mission_id: input.missionId,
      action: 'capture',
      proof_path: input.proofPath,
      amount_final: input.amountFinal,
      advance_actual: input.advanceActual,
    },
    { idempotencyKey: `pay-cap:${input.missionId}` },
  );
}
