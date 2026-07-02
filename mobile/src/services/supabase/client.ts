import 'react-native-url-polyfill/auto';

import { createClient } from '@supabase/supabase-js';
import { AppState } from 'react-native';

import { env } from '@/constants/env';
import type { Database } from '@/types/database.types';

import { largeSecureStore } from './secureStorage';

/**
 * Client Supabase UNIQUE de l'app (clé `anon` + JWT utilisateur uniquement).
 * `service_role` n'existe jamais côté mobile — il vit dans les Edge Functions.
 * La session est persistée de façon chiffrée (Keychain/Keystore) et rafraîchie
 * automatiquement.
 */
export const supabase = createClient<Database>(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    storage: largeSecureStore,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// Rafraîchissement du token lié au cycle de vie de l'app (reco Supabase/Expo).
AppState.addEventListener('change', (state) => {
  if (state === 'active') {
    void supabase.auth.startAutoRefresh();
  } else {
    void supabase.auth.stopAutoRefresh();
  }
});
