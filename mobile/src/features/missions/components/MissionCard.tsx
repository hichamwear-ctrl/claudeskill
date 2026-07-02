import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { formatDateTime, formatMoney } from '@/lib/format';
import { Card, Text, useTheme } from '@/ui';

import type { MissionListItem } from '../types';

import { StatusBadge } from './StatusBadge';

export interface MissionCardProps {
  item: MissionListItem;
  categoryLabel?: string;
  onPress: () => void;
}

/** Carte résumé d'une mission (statut, catégorie, prix, date). */
export function MissionCard({ item, categoryLabel, onPress }: MissionCardProps): ReactNode {
  const theme = useTheme();
  const price = item.final_amount ?? item.quoted_price ?? item.estimated_price;

  return (
    <Pressable onPress={onPress} accessibilityRole="button">
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text variant="heading">{categoryLabel ?? 'Demande'}</Text>
          <StatusBadge status={item.status} />
        </View>
        {item.dropoff_address ? (
          <Text variant="caption" color="textMuted">
            {item.dropoff_address}
          </Text>
        ) : null}
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: theme.spacing.xs }}>
          <Text variant="caption" color="textMuted">
            {formatDateTime(item.created_at)}
          </Text>
          <Text>{price !== null ? formatMoney(price) : 'Sur devis'}</Text>
        </View>
      </Card>
    </Pressable>
  );
}
