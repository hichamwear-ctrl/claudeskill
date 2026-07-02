import { useEffect, type ReactNode } from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useUiStore, type Toast } from '@/stores/uiStore';
import { useTheme, type ThemeColors } from '@/ui/theme';

import { Text } from '../primitives/Text';

function toneColor(colors: ThemeColors, tone: Toast['tone']): string {
  switch (tone) {
    case 'success':
      return colors.success;
    case 'error':
      return colors.danger;
    case 'info':
    default:
      return colors.primary;
  }
}

/** Hôte de rendu des toasts (monté une fois au niveau racine). */
export function ToastHost(): ReactNode {
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const toasts = useUiStore((s) => s.toasts);

  return (
    <View
      pointerEvents="box-none"
      style={{ position: 'absolute', left: 0, right: 0, bottom: insets.bottom + theme.spacing.lg, gap: theme.spacing.sm, paddingHorizontal: theme.spacing.lg }}
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} color={toneColor(theme.colors, toast.tone)} />
      ))}
    </View>
  );
}

function ToastItem({ toast, color }: { toast: Toast; color: string }): ReactNode {
  const theme = useTheme();
  const dismiss = useUiStore((s) => s.dismissToast);

  useEffect(() => {
    const id = setTimeout(() => dismiss(toast.id), 3500);
    return () => clearTimeout(id);
  }, [toast.id, dismiss]);

  return (
    <View
      style={{
        backgroundColor: theme.colors.text,
        borderRadius: theme.radius.md,
        paddingHorizontal: theme.spacing.lg,
        paddingVertical: theme.spacing.md,
        borderLeftWidth: 3,
        borderLeftColor: color,
      }}
    >
      <Text style={{ color: theme.colors.surface }}>{toast.message}</Text>
    </View>
  );
}
