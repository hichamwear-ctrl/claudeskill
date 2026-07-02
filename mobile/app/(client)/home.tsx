import type { ReactNode } from 'react';
import { View } from 'react-native';

import { Card, Screen, Text, useTheme } from '@/ui';

/**
 * C-07 (shell) — « De quoi avez-vous besoin ? ». La saisie libre + le dialogue
 * (converse) seront implémentés au module Intake. Ici : coquille sans logique.
 */
export default function Home(): ReactNode {
  const theme = useTheme();
  return (
    <Screen>
      <View style={{ gap: theme.spacing.lg }}>
        <Text variant="title">De quoi avez-vous besoin aujourd’hui ?</Text>
        <Card>
          <Text color="textMuted">
            La saisie libre du besoin et le dialogue guidé arriveront au prochain module (Intake).
          </Text>
        </Card>
      </View>
    </Screen>
  );
}
