import type { ReactNode } from 'react';
import { View } from 'react-native';

import { formatMoney } from '@/lib/format';
import { Card, Divider, Text, useTheme } from '@/ui';

import type { PriceEstimate } from '../types';

/** Détail du prix estimé (ou mention « sur devis » pour les catégories quote_only). */
export function PriceBreakdown({ estimate }: { estimate: PriceEstimate }): ReactNode {
  const theme = useTheme();
  const currency = estimate.currency.toUpperCase();

  if (estimate.quote_only || estimate.price === null) {
    return (
      <Card>
        <Text variant="heading">Sur devis</Text>
        <Text color="textMuted">Le prix sera fixé par l’opérateur après validation.</Text>
        <Text variant="caption" color="textMuted">Délai estimé : {estimate.eta_min} min</Text>
      </Card>
    );
  }

  const b = estimate.breakdown;
  return (
    <Card>
      <Text variant="heading">Estimation</Text>
      <View style={{ gap: theme.spacing.xs }}>
        <Row label="Base" value={formatMoney(b.base_fare, currency)} />
        <Row label={`Distance (${b.distance_km} km)`} value={formatMoney(b.distance_cost, currency)} />
        <Row label="Frais catégorie" value={formatMoney(b.category_base_fee, currency)} />
      </View>
      <Divider />
      <Row label="Total estimé" value={formatMoney(estimate.price, currency)} strong />
      <Text variant="caption" color="textMuted">Délai estimé : {estimate.eta_min} min</Text>
    </Card>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }): ReactNode {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
      <Text color={strong ? 'text' : 'textMuted'}>{label}</Text>
      <Text variant={strong ? 'heading' : 'body'}>{value}</Text>
    </View>
  );
}
