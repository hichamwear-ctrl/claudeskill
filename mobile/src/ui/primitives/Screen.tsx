import type { ReactNode } from 'react';
import { View, type ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme } from '@/ui/theme';

type ScreenEdge = 'top' | 'right' | 'bottom' | 'left';

export interface ScreenProps {
  children: ReactNode;
  /** Bords sûrs à appliquer (défaut : haut + bas). */
  edges?: readonly ScreenEdge[];
  padded?: boolean;
  style?: ViewStyle;
}

/** Conteneur d'écran : zone sûre + fond thémé + padding cohérent. */
export function Screen({
  children,
  edges = ['top', 'bottom'],
  padded = true,
  style,
}: ScreenProps): ReactNode {
  const theme = useTheme();
  return (
    <SafeAreaView
      edges={edges}
      style={{ flex: 1, backgroundColor: theme.colors.background }}
    >
      <View style={[{ flex: 1, padding: padded ? theme.spacing.lg : 0 }, style]}>{children}</View>
    </SafeAreaView>
  );
}
