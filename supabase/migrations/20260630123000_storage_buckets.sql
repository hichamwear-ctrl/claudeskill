-- ============================================================================
-- Storage — buckets & politiques d'accès
-- Réf. architecture §4.4 (buckets) et §14 (stockage des images)
--
-- Crée les buckets (tous PRIVÉS) et leurs policies sur storage.objects.
-- AUCUNE logique métier ici : le bucket mission-proofs est créé mais sa policy
-- « participant de la mission » sera ajoutée avec le modèle métier (la table
-- missions n'existe pas encore).
--
-- Convention de chemin (1er segment = dossier de scoping) :
--   avatars/        {user_id}/<fichier>
--   request-photos/ {user_id}/<fichier>      (rattachement mission : étape métier)
--   documents/      {user_id}/<fichier>       (usage futur)
--   mission-proofs/ {mission_id}/<fichier>    (accès participants : étape métier)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) Buckets — privés, avec limites de taille et types MIME autorisés.
--    Idempotent (on conflict) pour rejouer la migration sans erreur.
-- ----------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('avatars',        'avatars',        false,  5242880,
     array['image/png','image/jpeg','image/webp']),
  ('request-photos', 'request-photos', false, 10485760,
     array['image/png','image/jpeg','image/webp','image/heic']),
  ('mission-proofs', 'mission-proofs', false, 10485760,
     array['image/png','image/jpeg','image/webp','image/heic','application/pdf']),
  ('documents',      'documents',      false, 10485760,
     array['image/png','image/jpeg','application/pdf'])
on conflict (id) do nothing;

-- ----------------------------------------------------------------------------
-- 2) Politiques RLS sur storage.objects
--    Motif « propriétaire » : 1er segment du chemin = (auth.uid()).
-- ----------------------------------------------------------------------------

-- avatars : chaque utilisateur gère uniquement ses propres fichiers.
create policy "avatars_owner_rw" on storage.objects
  for all to authenticated
  using      (bucket_id = 'avatars'        and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'avatars'        and (storage.foldername(name))[1] = (select auth.uid())::text);

-- request-photos : dossier = uid de l'uploadeur (rattachement mission ultérieur).
create policy "request_photos_owner_rw" on storage.objects
  for all to authenticated
  using      (bucket_id = 'request-photos' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'request-photos' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- documents : usage futur ; dossier = uid propriétaire.
create policy "documents_owner_rw" on storage.objects
  for all to authenticated
  using      (bucket_id = 'documents'      and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'documents'      and (storage.foldername(name))[1] = (select auth.uid())::text);

-- mission-proofs : AUCUNE policy utilisateur pour l'instant. Accès refusé par
-- défaut côté client (RLS) ; seules les Edge Functions (service_role) écrivent.
-- La policy « participant de la mission » sera ajoutée avec la table missions (§8.7).

-- Admin : accès complet à tous les buckets (back-office / support / modération).
create policy "storage_admin_all" on storage.objects
  for all to authenticated
  using      (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');
