/**
 * Types de domaine dérivés du schéma généré. Aucun statut/rôle en `string`
 * libre : tout provient des enums de `database.types.ts`.
 */
import type { Enums, Tables } from './database.types';

export type UserRole = Enums<'user_role'>;
export type MissionStatus = Enums<'mission_status'>;
export type PaymentStatus = Enums<'payment_status'>;
export type MissionFamily = Enums<'mission_family'>;
export type QuestionType = Enums<'question_type'>;

export type Profile = Tables<'profiles'>;
export type Mission = Tables<'missions'>;
export type Message = Tables<'messages'>;
export type Notification = Tables<'notifications'>;
export type ServiceCategory = Tables<'service_categories'>;

/** État de session applicatif (miroir client de la session Supabase + rôle JWT). */
export type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated';

/** Claim métier injecté par le hook `custom_access_token_hook`. */
export interface AppJwtClaims {
  sub?: string;
  user_role?: UserRole;
  exp?: number;
}
