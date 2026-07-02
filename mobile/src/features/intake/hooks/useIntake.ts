import { useMutation, useQuery } from '@tanstack/react-query';

import {
  converse,
  estimatePrice,
  submitRequest,
  zoneCheck,
  type Coordinates,
} from '../api/intake';

/** Tour de dialogue (mutation : chaque appel fait avancer le moteur). */
export function useConverse() {
  return useMutation({ mutationFn: converse });
}

/** Clôture de l'intake. */
export function useSubmitRequest() {
  return useMutation({ mutationFn: submitRequest });
}

/** Couverture/horaires (activé quand des coordonnées sont disponibles). */
export function useZoneCheck(coords: Coordinates | null) {
  return useQuery({
    queryKey: ['zone-check', coords?.lat, coords?.lng],
    queryFn: () => zoneCheck(coords as Coordinates),
    enabled: Boolean(coords),
    staleTime: 60_000,
  });
}

/** Estimation prix (activée quand catégorie + coordonnées sont disponibles). */
export function useEstimatePrice(categoryId: string | null, coords: Coordinates | null) {
  return useQuery({
    queryKey: ['estimate-price', categoryId, coords?.lat, coords?.lng],
    queryFn: () => estimatePrice({ category_id: categoryId as string, dropoff: coords as Coordinates }),
    enabled: Boolean(categoryId && coords),
    staleTime: 60_000,
  });
}
