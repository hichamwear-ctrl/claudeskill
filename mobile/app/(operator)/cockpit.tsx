import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { routes } from '@/constants/routes';
import { useMyProfile, useSignOut } from '@/features/auth';
import { useAvailability } from '@/features/operator';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Badge, Button, Card, Screen, Text, useTheme } from '@/ui';

/** OP-03 — Cockpit : disponibilité (Presence), accès revue/missions, session. */
export default function Cockpit(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const profile = useMyProfile();
  const signOut = useSignOut();
  const availability = useAvailability();
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
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text>{availability.online ? 'Disponible' : 'Indisponible'}</Text>
            <Badge label={availability.online ? 'En ligne' : 'Hors ligne'} tone={availability.online ? 'success' : 'neutral'} />
          </View>
          <Button
            label={availability.online ? 'Se mettre indisponible' : 'Se rendre disponible'}
            variant={availability.online ? 'secondary' : 'primary'}
            onPress={() => availability.setOnline(!availability.online)}
          />
        </Card>
        <Button label="Demandes à valider" onPress={() => router.push(routes.operatorReview)} />
        <Button label="Missions assignées" variant="secondary" onPress={() => router.push(routes.operatorWork)} />
        <Button label="Se déconnecter" variant="destructive" onPress={onSignOut} loading={signOut.isPending} />
      </View>
    </Screen>
  );
}
