import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { routes } from '@/constants/routes';
import { useMyProfile, useSignOut } from '@/features/auth';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Badge, Button, Card, Screen, Text, useTheme } from '@/ui';

/**
 * OP-03 (shell) — Cockpit. Disponibilité (Presence) + file de revue arriveront
 * au module Cockpit. Ici : coquille + accès revue + déconnexion (session réelle).
 */
export default function Cockpit(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const profile = useMyProfile();
  const signOut = useSignOut();
  const showToast = useUiStore((s) => s.showToast);

  const onSignOut = async () => {
    try {
      await signOut.mutateAsync();
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  return (
    <Screen>
      <View style={{ gap: theme.spacing.lg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text variant="title">Cockpit</Text>
          {profile.data?.role ? <Badge label={profile.data.role} tone="primary" /> : null}
        </View>
        <Card>
          <Text color="textMuted">En attente de demandes. La file de revue en temps réel arrivera au module Cockpit.</Text>
        </Card>
        <Button label="Demandes à valider" onPress={() => router.push(routes.operatorReview)} />
        <Button label="Se déconnecter" variant="destructive" onPress={onSignOut} loading={signOut.isPending} />
      </View>
    </Screen>
  );
}
