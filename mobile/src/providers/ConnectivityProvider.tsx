import NetInfo from '@react-native-community/netinfo';
import { focusManager, onlineManager } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';
import { AppState, Platform, type AppStateStatus } from 'react-native';

import { useConnectivityStore } from '@/stores/connectivityStore';

/**
 * Branche NetInfo → `onlineManager` (React Query) + `connectivityStore`
 * (bannière hors-ligne), et AppState → `focusManager` (refetch au retour au
 * premier plan).
 */
export function ConnectivityProvider({ children }: { children: ReactNode }): ReactNode {
  const setOnline = useConnectivityStore((s) => s.setOnline);

  useEffect(() => {
    const unsubscribeNet = NetInfo.addEventListener((state) => {
      const online = Boolean(state.isConnected && (state.isInternetReachable ?? true));
      setOnline(online);
      onlineManager.setOnline(online);
    });

    const appStateSub = AppState.addEventListener('change', (status: AppStateStatus) => {
      if (Platform.OS !== 'web') focusManager.setFocused(status === 'active');
    });

    return () => {
      unsubscribeNet();
      appStateSub.remove();
    };
  }, [setOnline]);

  return children;
}
