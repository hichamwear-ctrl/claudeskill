/**
 * In-app audio call abstraction (Phase 5).
 *
 * A mock provider runs by default so the whole call lifecycle (start → in
 * progress → end) works end-to-end without any third party. To go live, set
 * `CALL_PROVIDER=twilio` with Twilio Voice credentials — the API routes and UI
 * never change, they only ever talk to this interface.
 */
export interface CreateCallInput {
  reservationId: string;
  initiatorId: string;
}

export interface CreateCallResult {
  /** Opaque room / conference identifier. */
  room: string;
  /** Access token for the client SDK (Twilio). Absent for the mock. */
  token?: string;
  provider: string;
  /** Human-readable note surfaced in the UI (e.g. demo-mode explanation). */
  note?: string;
}

export interface CallProvider {
  readonly name: string;
  createCall(input: CreateCallInput): Promise<CreateCallResult>;
  endCall(room: string): Promise<void>;
}
