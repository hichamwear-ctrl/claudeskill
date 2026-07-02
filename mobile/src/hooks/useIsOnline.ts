import { useConnectivityStore } from '@/stores/connectivityStore';

/** Indique si l'app est en ligne (alimenté par NetInfo via ConnectivityProvider). */
export function useIsOnline(): boolean {
  return useConnectivityStore((s) => s.isOnline);
}
