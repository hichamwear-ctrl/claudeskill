import type { ReactNode } from 'react';

import { EmptyState, Screen } from '@/ui';

/**
 * Variante WEB : `react-native-maps` n'est pas compatible navigateur.
 * Metro choisit ce fichier `.web.tsx` sur le web et le `.tsx` (carte native)
 * sur iOS/Android — la carte n'est donc jamais chargée dans le navigateur.
 */
export function MissionMapScreen(): ReactNode {
  return (
    <Screen padded={false}>
      <EmptyState
        title="Carte indisponible sur navigateur"
        message="Le suivi sur carte est disponible uniquement sur l’app mobile."
      />
    </Screen>
  );
}
