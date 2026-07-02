import { create } from 'zustand';

export type ToastTone = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  tone: ToastTone;
  message: string;
}

interface UiStoreState {
  toasts: Toast[];
  showToast: (tone: ToastTone, message: string) => void;
  dismissToast: (id: string) => void;
}

/** File de feedback (toasts/bannières). Rendu assuré par un hôte au niveau racine. */
export const useUiStore = create<UiStoreState>((set) => ({
  toasts: [],
  showToast: (tone, message) =>
    set((state) => ({
      toasts: [...state.toasts, { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, tone, message }],
    })),
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
