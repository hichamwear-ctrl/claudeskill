import type { ReactNode } from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useIsOnline } from '@/hooks/useIsOnline';

import { Banner } from './Banner';

/** Bannière persistante affichée en haut quand l'app est hors connexion. */
export function OfflineBanner(): ReactNode {
  const insets = useSafeAreaInsets();
  const online = useIsOnline();
  if (online) return null;
  return (
    <View style={{ position: 'absolute', top: insets.top, left: 0, right: 0 }} pointerEvents="none">
      <Banner tone="warning" message="Hors connexion — certaines actions sont indisponibles." />
    </View>
  );
}
