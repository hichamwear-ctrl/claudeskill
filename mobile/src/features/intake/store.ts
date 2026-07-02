import { create } from 'zustand';

import type { TurnResult } from './types';

interface IntakeStoreState {
  /** Dernier tour connu (partagé entre Home → Conversation → Récapitulatif). */
  turn: TurnResult | null;
  setTurn: (turn: TurnResult) => void;
  reset: () => void;
}

/** État éphémère du dialogue en cours (non persisté). */
export const useIntakeStore = create<IntakeStoreState>((set) => ({
  turn: null,
  setTurn: (turn) => set({ turn }),
  reset: () => set({ turn: null }),
}));
