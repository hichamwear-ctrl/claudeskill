import { create } from 'zustand';

interface ConnectivityStoreState {
  /** `true` par défaut (optimiste) ; alimenté par NetInfo via ConnectivityProvider. */
  isOnline: boolean;
  setOnline: (isOnline: boolean) => void;
}

export const useConnectivityStore = create<ConnectivityStoreState>((set) => ({
  isOnline: true,
  setOnline: (isOnline) => set({ isOnline }),
}));
