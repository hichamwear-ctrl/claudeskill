import { useQuery } from '@tanstack/react-query';

import { qk } from '@/constants/queryKeys';

import { pingHealth, type HealthStatus } from '../api/health';

/** Interroge la sonde backend. Non mis en cache longtemps (diagnostic). */
export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: qk.health(),
    queryFn: pingHealth,
    retry: 1,
    staleTime: 0,
    gcTime: 0,
  });
}
