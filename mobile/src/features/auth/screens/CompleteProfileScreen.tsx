import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { View } from 'react-native';
import { z } from 'zod';

import { routes } from '@/constants/routes';
import { useRole } from '@/hooks/useSession';
import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, Input, Screen, Text, useTheme } from '@/ui';

import { useUpdateProfile } from '../hooks/useProfile';

const schema = z.object({
  first_name: z.string().min(1, 'Le prénom est requis'),
});
type FormValues = z.infer<typeof schema>;

/** C-05 — Complétion du profil (prénom). Réutilisable depuis Profil. */
export function CompleteProfileScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const role = useRole();
  const updateProfile = useUpdateProfile();
  const showToast = useUiStore((s) => s.showToast);

  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: '' },
  });

  const onSubmit = handleSubmit(async ({ first_name }) => {
    try {
      await updateProfile.mutateAsync({ first_name });
      const target = role === 'operator' || role === 'admin' ? routes.operatorCockpit : routes.clientHome;
      router.replace(target);
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  });

  return (
    <Screen>
      <View style={{ flex: 1, gap: theme.spacing.lg, justifyContent: 'center' }}>
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="title">Votre prénom</Text>
          <Text color="textMuted">Pour personnaliser votre expérience.</Text>
        </View>
        <Card>
          <Controller
            control={control}
            name="first_name"
            render={({ field, fieldState }) => (
              <Input
                label="Prénom"
                placeholder="Camille"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
              />
            )}
          />
          <Button label="Enregistrer" onPress={onSubmit} loading={updateProfile.isPending} />
        </Card>
      </View>
    </Screen>
  );
}
