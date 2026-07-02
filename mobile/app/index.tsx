import { Redirect } from 'expo-router';
import type { ReactNode } from 'react';

/**
 * Point d'entrée (bootstrap). En MOBILE 1, redirige vers l'écran de diagnostic
 * `health`. Au module M3, cette route décidera de la destination selon la
 * session et le rôle (auth / client / operator).
 */
export default function Index(): ReactNode {
  return <Redirect href="/health" />;
}
