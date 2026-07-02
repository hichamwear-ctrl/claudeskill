import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { View } from 'react-native';
import { z } from 'zod';

import { routes } from '@/constants/routes';
import { toUxError } from '@/lib/errorCatalog';
import { supabase } from '@/services/supabase/client';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, Input, Screen, Text, useTheme } from '@/ui';

import { useRequestOtp } from '../hooks/useAuth';

const schema = z.object({
  email: z.string().email('Adresse e-mail invalide'),
});
type FormValues = z.infer<typeof schema>;

/** C-03 — Connexion. Démo : OTP e-mail + entrée « mode démo » (anonyme, sans e-mail). */
export function SignInScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const requestOtp = useRequestOtp();
  const showToast = useUiStore((s) => s.showToast);

  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '' },
  });

  const onSubmit = handleSubmit(async ({ email }) => {
    try {
      await requestOtp.mutateAsync(email);
      router.push({ pathname: routes.verifyOtp, params: { email } });
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  });

  const onDemo = async () => {
    const { error } = await supabase.auth.signInAnonymously();
    if (error) showToast('error', `Mode démo indisponible : ${error.message}`);
    // Succès : la garde redirige automatiquement vers l'accueil client.
  };

  return (
    <Screen>
      <View style={{ flex: 1, gap: theme.spacing.lg, justifyContent: 'center' }}>
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="title">Bienvenue</Text>
          <Text color="textMuted">Connectez-vous pour continuer.</Text>
        </View>

        <Card>
          <Controller
            control={control}
            name="email"
            render={({ field, fieldState }) => (
              <Input
                label="Adresse e-mail"
                placeholder="vous@exemple.fr"
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
              />
            )}
          />
          <Button label="Recevoir le code" onPress={onSubmit} loading={requestOtp.isPending} />
        </Card>

        <Button label="Entrer en mode démo (sans e-mail)" variant="secondary" onPress={onDemo} />
        <Text variant="caption" color="textMuted" style={{ textAlign: 'center' }}>
          Le mode démo vous connecte en tant que client pour tester l’application.
        </Text>
      </View>
    </Screen>
  );
}
