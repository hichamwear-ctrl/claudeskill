/**
 * Lecture + validation des variables d'environnement publiques.
 * Aucune valeur secrète (uniquement `EXPO_PUBLIC_*`). En cas d'absence,
 * `isConfigured` passe à `false` : l'écran Health le signale clairement
 * plutôt que de faire planter l'app.
 */
const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

export const env = {
  supabaseUrl,
  supabaseAnonKey,
  apiVersion: process.env.EXPO_PUBLIC_API_VERSION ?? '1',
  isConfigured: supabaseUrl.length > 0 && supabaseAnonKey.length > 0,
} as const;
