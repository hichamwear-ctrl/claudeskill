/**
 * Typage des variables d'environnement exposées au client Expo.
 * Seules les variables préfixées `EXPO_PUBLIC_` sont injectées dans le bundle
 * (jamais de secret ici — cf. `docs/EXPO_DEMO_SETUP.md`).
 */
declare namespace NodeJS {
  interface ProcessEnv {
    readonly EXPO_PUBLIC_SUPABASE_URL: string;
    readonly EXPO_PUBLIC_SUPABASE_ANON_KEY: string;
    readonly EXPO_PUBLIC_API_VERSION?: string;
  }
}
