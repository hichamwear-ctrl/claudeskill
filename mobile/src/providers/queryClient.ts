import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { QueryClient } from '@tanstack/react-query';

/**
 * QueryClient partagé + persistance AsyncStorage (lecture hors-ligne du
 * référentiel et des dernières données). Les paliers de fraîcheur fins
 * (référentiel long / missions court / temps réel) seront réglés par requête.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      gcTime: 1000 * 60 * 60 * 24, // 24 h : survit à la persistance
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0, // jamais de rejeu implicite (paiement/transitions = non idempotents côté UX)
    },
  },
});

export const asyncStoragePersister = createAsyncStoragePersister({
  storage: AsyncStorage,
  key: 'rq-cache',
});
