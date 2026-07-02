import * as Location from 'expo-location';
import { useEffect, useState } from 'react';

export interface Coords {
  lat: number;
  lng: number;
}

export interface LocationState {
  status: 'loading' | 'granted' | 'denied' | 'error';
  coords: Coords | null;
}

/**
 * Position courante (foreground, à l'usage). Utilisé pour zone-check /
 * estimate-price. Permission refusée → `denied` (l'écran dégrade proprement).
 */
export function useCurrentLocation(enabled = true): LocationState {
  const [state, setState] = useState<LocationState>({ status: 'loading', coords: null });

  useEffect(() => {
    if (!enabled) return;
    let mounted = true;

    void (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        if (mounted) setState({ status: 'denied', coords: null });
        return;
      }
      try {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        if (mounted) {
          setState({ status: 'granted', coords: { lat: pos.coords.latitude, lng: pos.coords.longitude } });
        }
      } catch {
        if (mounted) setState({ status: 'error', coords: null });
      }
    })();

    return () => {
      mounted = false;
    };
  }, [enabled]);

  return state;
}
