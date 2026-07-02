import type { ReactNode } from 'react';
import { View } from 'react-native';

import { formatDateTime } from '@/lib/format';
import { Card, Text, useTheme } from '@/ui';

import { missionStatusLabel } from '../status';
import type { MissionEvent } from '../types';

/** Frise des transitions de statut (à partir de `mission_events`). */
export function MissionTimeline({ events }: { events: MissionEvent[] }): ReactNode {
  const theme = useTheme();
  if (events.length === 0) {
    return (
      <Card>
        <Text color="textMuted">Aucun événement pour l’instant.</Text>
      </Card>
    );
  }
  return (
    <Card>
      <Text variant="heading">Progression</Text>
      <View style={{ gap: theme.spacing.sm, marginTop: theme.spacing.xs }}>
        {events.map((event) => (
          <View key={event.id} style={{ flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm }}>
            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.primary }} />
            <View style={{ flex: 1 }}>
              <Text>{event.to_status ? missionStatusLabel(event.to_status) : '—'}</Text>
              {event.reason ? (
                <Text variant="caption" color="textMuted">
                  {event.reason}
                </Text>
              ) : null}
            </View>
            <Text variant="caption" color="textMuted">
              {formatDateTime(event.created_at)}
            </Text>
          </View>
        ))}
      </View>
    </Card>
  );
}
