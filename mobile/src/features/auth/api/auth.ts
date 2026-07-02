import { AppError } from '@/lib/errors';
import { unwrap } from '@/services/api';
import { supabase } from '@/services/supabase/client';
import type { Profile } from '@/types/domain';

/** Envoie un code OTP par e-mail (crée l'utilisateur au besoin). */
export async function requestEmailOtp(email: string): Promise<void> {
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: true },
  });
  if (error) throw new AppError('bad_request', error.message, 400);
}

/** Vérifie le code OTP e-mail → ouvre la session (déclenche onAuthStateChange). */
export async function verifyEmailOtp(email: string, token: string): Promise<void> {
  const { error } = await supabase.auth.verifyOtp({ email, token, type: 'email' });
  if (error) throw new AppError('validation_failed', error.message, 422);
}

/** Ferme la session. */
export async function signOut(): Promise<void> {
  const { error } = await supabase.auth.signOut();
  if (error) throw new AppError('internal_error', error.message, 500);
}

/** Profil de l'utilisateur courant (RLS : propriétaire). */
export async function fetchMyProfile(userId: string): Promise<Profile> {
  return unwrap(supabase.from('profiles').select('*').eq('id', userId).single());
}

export interface ProfilePatch {
  first_name?: string;
  last_name?: string;
  locale?: string;
}

/** Met à jour son profil (jamais le rôle — garde anti-escalade côté base). */
export async function updateMyProfile(userId: string, patch: ProfilePatch): Promise<Profile> {
  return unwrap(supabase.from('profiles').update(patch).eq('id', userId).select('*').single());
}
