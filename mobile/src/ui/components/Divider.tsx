import type { ReactNode } from 'react';
import { View } from 'react-native';

import { useTheme } from '@/ui/theme';

/** Séparateur horizontal fin (1 px, couleur de bordure). */
export function Divider(): ReactNode {
  const theme = useTheme();
  return <View style={{ height: 1, backgroundColor: theme.colors.border }} />;
}
