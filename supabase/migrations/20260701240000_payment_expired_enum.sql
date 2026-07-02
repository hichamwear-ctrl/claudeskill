-- ============================================================================
-- M9 — Ajout de la valeur `expired` à payment_status (autorisation expirée).
-- Réf. BUSINESS_RULES BR-214, SPEC §5.
--
-- Migration ISOLÉE : `ALTER TYPE ... ADD VALUE` doit être committé avant d'être
-- utilisé (par les fonctions/jobs de la migration suivante).
-- ============================================================================
alter type public.payment_status add value if not exists 'expired';
