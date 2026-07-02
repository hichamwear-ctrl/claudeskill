import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { routes } from '@/constants/routes';
import { useMyProfile, useSignOut } from '@/features/auth';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Avatar, Badge, Button, Card, ErrorState, Loader, Screen, Text, useTheme } from '@/ui';

/** C-29 / OP-14 — Profil & paramètres (partagé). Shell : infos + déconnexion. */
export function ProfileScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const profile = useMyProfile();
  const signOut = useSignOut();
  const showToast = useUiStore((s) => s.showToast);

  const onSignOut = async () => {
    try {
      await signOut.mutateAsync();
      // La garde redirige vers /sign-in dès la session fermée.
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  if (profile.isLoading) return <Screen><Loader fill label="Chargement du profil…" /></Screen>;
  if (profile.isError) return <Screen><ErrorState error={profile.error} onRetry={() => profile.refetch()} /></Screen>;

  const data = profile.data;
  const displayName = data?.first_name ?? 'Profil';

  return (
    <Screen>
      <View style={{ gap: theme.spacing.lg }}>
        <Text variant="title">Profil</Text>

        <Card>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md }}>
            <Avatar uri={data?.avatar_url} name={displayName} size={48} />
            <View style={{ flex: 1, gap: 4 }}>
              <Text variant="heading">{displayName}</Text>
              <Text variant="caption" color="textMuted">
                {data?.email ?? data?.phone ?? '—'}
              </Text>
            </View>
            {data?.role ? <Badge label={data.role} tone="primary" /> : null}
          </View>
        </Card>

        <Button
          label="Compléter le profil"
          variant="secondary"
          onPress={() => router.push(routes.completeProfile)}
        />
        <Button label="Se déconnecter" variant="destructive" onPress={onSignOut} loading={signOut.isPending} />
      </View>
    </Screen>
  );
}
