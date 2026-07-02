import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import type { ReactNode } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import '@/services/i18n'; // initialise i18next (couche shell)
import { asyncStoragePersister, queryClient } from '@/providers/queryClient';
import { ThemeProvider } from '@/ui/theme';

import { ConnectivityProvider } from './ConnectivityProvider';
import { SessionProvider } from './SessionProvider';

/**
 * Compose tous les providers racine dans le bon ordre :
 * gestes → zone sûre → cache (persisté) → thème → connectivité → session.
 */
export function AppProviders({ children }: { children: ReactNode }): ReactNode {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{ persister: asyncStoragePersister }}
        >
          <ThemeProvider>
            <ConnectivityProvider>
              <SessionProvider>{children}</SessionProvider>
            </ConnectivityProvider>
          </ThemeProvider>
        </PersistQueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
