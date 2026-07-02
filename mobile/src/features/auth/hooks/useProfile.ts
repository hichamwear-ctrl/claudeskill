import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { qk } from '@/constants/queryKeys';
import { useUserId } from '@/hooks/useSession';

import { fetchMyProfile, updateMyProfile, type ProfilePatch } from '../api/auth';

/** Profil de l'utilisateur courant (désactivé tant qu'aucune session). */
export function useMyProfile() {
  const userId = useUserId();
  return useQuery({
    queryKey: qk.profile.me(),
    queryFn: () => fetchMyProfile(userId as string),
    enabled: Boolean(userId),
  });
}

/** Mise à jour du profil courant + invalidation du cache. */
export function useUpdateProfile() {
  const userId = useUserId();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: ProfilePatch) => updateMyProfile(userId as string, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.profile.me() });
    },
  });
}
