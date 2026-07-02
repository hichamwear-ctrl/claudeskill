import { useLocalSearchParams } from 'expo-router';
import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { toUxError } from '@/lib/errorCatalog';
import { useUiStore } from '@/stores/uiStore';
import { Button, Card, Input, Screen, Text, useTheme } from '@/ui';

import { useRequestOtp, useVerifyOtp } from '../hooks/useAuth';

/**
 * C-04 — Saisie du code OTP. À la vérification, la session s'ouvre et la garde
 * du groupe (auth) redirige automatiquement vers l'accueil du rôle.
 */
export function VerifyOtpScreen(): ReactNode {
  const theme = useTheme();
  const params = useLocalSearchParams<{ email?: string }>();
  const email = params.email ?? '';
  const [code, setCode] = useState('');
  const verifyOtp = useVerifyOtp();
  const requestOtp = useRequestOtp();
  const showToast = useUiStore((s) => s.showToast);

  const onVerify = async () => {
    try {
      await verifyOtp.mutateAsync({ email, token: code.trim() });
      // Pas de navigation manuelle : la garde (auth) redirige sur session ouverte.
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  const onResend = async () => {
    try {
      await requestOtp.mutateAsync(email);
      showToast('info', 'Nouveau code envoyé.');
    } catch (error) {
      showToast('error', toUxError(error).message);
    }
  };

  return (
    <Screen>
      <View style={{ flex: 1, gap: theme.spacing.lg, justifyContent: 'center' }}>
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="title">Vérification</Text>
          <Text color="textMuted">Entrez le code à 6 chiffres envoyé à {email || 'votre e-mail'}.</Text>
        </View>

        <Card>
          <Input
            label="Code de vérification"
            placeholder="000000"
            keyboardType="number-pad"
            maxLength={6}
            value={code}
            onChangeText={setCode}
          />
          <Button
            label="Valider"
            onPress={onVerify}
            loading={verifyOtp.isPending}
            disabled={code.trim().length < 6}
          />
        </Card>

        <Button label="Renvoyer le code" variant="ghost" onPress={onResend} loading={requestOtp.isPending} />
      </View>
    </Screen>
  );
}
