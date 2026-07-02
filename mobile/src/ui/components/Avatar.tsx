import type { ReactNode } from 'react';
import { Image, View } from 'react-native';

import { useTheme } from '@/ui/theme';

import { Text } from '../primitives/Text';

export interface AvatarProps {
  uri?: string | null;
  name?: string | null;
  size?: number;
}

function initials(name?: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p.charAt(0).toUpperCase()).join('') || '?';
}

/** Avatar : image (bucket `avatars`) sinon initiales sur pastille colorée. */
export function Avatar({ uri, name, size = 40 }: AvatarProps): ReactNode {
  const theme = useTheme();
  if (uri) {
    return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: size / 2 }} />;
  }
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: theme.colors.surfaceMuted,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text variant="caption" color="textMuted">
        {initials(name)}
      </Text>
    </View>
  );
}
