import { Link, Stack } from 'expo-router';
import type { ReactNode } from 'react';

import { Screen, Text } from '@/ui';

export default function NotFound(): ReactNode {
  return (
    <>
      <Stack.Screen options={{ title: 'Introuvable' }} />
      <Screen>
        <Text variant="heading">Page introuvable</Text>
        <Link href="/">
          <Text color="primary">Retour à l’accueil</Text>
        </Link>
      </Screen>
    </>
  );
}
