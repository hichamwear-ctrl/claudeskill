import { useRouter } from 'expo-router';
import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { routes } from '@/constants/routes';
import { Button, Screen, Text, useTheme } from '@/ui';

const SLIDES = [
  { icon: '💬', title: 'Exprimez votre besoin', body: 'Dites simplement ce qu’il vous faut, en langage naturel.' },
  { icon: '✅', title: 'Validation humaine', body: 'Un opérateur valide votre demande avant tout paiement.' },
  { icon: '📍', title: 'Suivi en temps réel', body: 'Suivez l’avancement et l’intervenant en direct.' },
];

/** C-02 — Onboarding très court (2–3 écrans, skippable). */
export function OnboardingScreen(): ReactNode {
  const theme = useTheme();
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const slide = SLIDES[index];
  const isLast = index === SLIDES.length - 1;

  const goToSignIn = () => router.replace(routes.signIn);

  return (
    <Screen>
      <View style={{ alignItems: 'flex-end' }}>
        <Button label="Passer" variant="ghost" onPress={goToSignIn} />
      </View>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: theme.spacing.md }}>
        <Text variant="title">{slide?.icon}</Text>
        <Text variant="heading" style={{ textAlign: 'center' }}>
          {slide?.title}
        </Text>
        <Text color="textMuted" style={{ textAlign: 'center' }}>
          {slide?.body}
        </Text>
      </View>
      <Button
        label={isLast ? 'Commencer' : 'Suivant'}
        onPress={() => (isLast ? goToSignIn() : setIndex((i) => i + 1))}
      />
    </Screen>
  );
}
