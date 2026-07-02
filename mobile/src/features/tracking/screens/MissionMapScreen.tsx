import { useLocalSearchParams } from 'expo-router';
import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';

import { EmptyState, Loader, Screen } from '@/ui';

import { useOperatorLocation } from '../hooks/useTracking';

/** C-19 — Suivi carte : position de l'intervenant (repli sondage). */
export function MissionMapScreen(): ReactNode {
  const { id } = useLocalSearchParams<{ id: string }>();
  const location = useOperatorLocation(id);

  if (location.isLoading) return <Screen><Loader fill label="Localisation…" /></Screen>;

  const coords = location.data;
  if (!coords) {
    return (
      <Screen padded={false}>
        <EmptyState icon="📍" title="Position indisponible" message="L’intervenant n’est pas encore en déplacement." />
      </Screen>
    );
  }

  return (
    <View style={StyleSheet.absoluteFill}>
      <MapView
        provider={PROVIDER_DEFAULT}
        style={StyleSheet.absoluteFill}
        region={{
          latitude: coords.lat,
          longitude: coords.lng,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }}
      >
        <Marker coordinate={{ latitude: coords.lat, longitude: coords.lng }} title="Intervenant" />
      </MapView>
    </View>
  );
}
