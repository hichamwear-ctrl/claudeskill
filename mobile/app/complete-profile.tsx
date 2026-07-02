import { Redirect } from 'expo-router';
import type { ReactNode } from 'react';

import { routes } from '@/constants/routes';
import { CompleteProfileScreen } from '@/features/auth';
import { useSessionStatus } from '@/hooks/useSession';
import { Loader, Screen } from '@/ui';

/**
 * Route neutre (hors groupe) : la complétion de profil concerne un utilisateur
 * DÉJÀ connecté (atteinte depuis Profil ou l'onboarding). Redirige vers l'auth
 * si aucune session.
 */
export default function CompleteProfile(): ReactNode {
  const status = useSessionStatus();
  if (status === 'loading') {
    return (
      <Screen>
        <Loader fill />
      </Screen>
    );
  }
  if (status === 'unauthenticated') return <Redirect href={routes.signIn} />;
  return <CompleteProfileScreen />;
}
