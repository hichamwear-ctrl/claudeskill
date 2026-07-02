import type { ReactNode } from 'react';
import { Modal as RNModal, Pressable } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from '../primitives/Text';

export interface ModalProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

/** Feuille modale centrée (confirmations, sélections). */
export function Modal({ visible, onClose, title, children }: ModalProps): ReactNode {
  const theme = useTheme();
  return (
    <RNModal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable
        onPress={onClose}
        style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'center', padding: theme.spacing.xl }}
      >
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            backgroundColor: theme.colors.surface,
            borderRadius: theme.radius.lg,
            padding: theme.spacing.lg,
            gap: theme.spacing.md,
          }}
        >
          {title ? <Text variant="heading">{title}</Text> : null}
          {children}
        </Pressable>
      </Pressable>
    </RNModal>
  );
}
