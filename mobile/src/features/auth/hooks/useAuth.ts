import { useMutation } from '@tanstack/react-query';

import { requestEmailOtp, signOut, verifyEmailOtp } from '../api/auth';

/** Demande d'envoi du code OTP par e-mail. */
export function useRequestOtp() {
  return useMutation({ mutationFn: (email: string) => requestEmailOtp(email) });
}

/** Vérification du code OTP (ouvre la session). */
export function useVerifyOtp() {
  return useMutation({
    mutationFn: (vars: { email: string; token: string }) => verifyEmailOtp(vars.email, vars.token),
  });
}

/** Déconnexion (la redirection est gérée par les gardes via le sessionStore). */
export function useSignOut() {
  return useMutation({ mutationFn: signOut });
}
