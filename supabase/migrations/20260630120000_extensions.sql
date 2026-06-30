-- ============================================================================
-- Socle technique — Extensions PostgreSQL
-- Réf. architecture §4.2 « PostgreSQL (+ extensions) »
--
-- Cette migration n'active QUE les capacités de base de la plateforme.
-- Aucune table métier n'est créée ici (missions, commandes, services... sont
-- volontairement reportées tant que le PRD et la Spec UX ne sont pas finalisés).
-- ============================================================================

-- Schéma dédié aux extensions : convention Supabase pour ne pas polluer `public`.
create schema if not exists extensions;

-- Identifiants & cryptographie
--   - uuid-ossp : génération d'UUID (fallback historique)
--   - pgcrypto  : gen_random_uuid(), hashing, chiffrement applicatif
create extension if not exists "uuid-ossp" with schema extensions;
create extension if not exists pgcrypto    with schema extensions;

-- Géospatial : zones de couverture, points d'adresse, distances/ETA (PostGIS).
create extension if not exists postgis      with schema extensions;

-- Appels HTTP sortants depuis la base : déclenchement des webhooks de transition
-- (ex. Database Webhook -> Edge Function send-push). Schéma `net` imposé par l'extension.
create extension if not exists pg_net;

-- Tâches planifiées : expiration de devis, purge des tracés, recalcul d'agrégats.
create extension if not exists pg_cron;
