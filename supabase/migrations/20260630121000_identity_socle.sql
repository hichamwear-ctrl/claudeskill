-- ============================================================================
-- Socle d'identité — rôles, profils, création automatique, RLS
-- Réf. architecture §5 (rôles & autorisation) et §6.2 (profiles)
--
-- Périmètre STRICT : identité uniquement. Aucune table métier.
-- Les trois rôles (client / operator / admin) sont modélisés dès maintenant :
-- les utiliser plus tard ne demandera AUCUNE migration de structure.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) Enum des rôles applicatifs
-- ----------------------------------------------------------------------------
create type public.user_role as enum ('client', 'operator', 'admin');

comment on type public.user_role is
  'Rôles applicatifs. Évolutif : ajouter un rôle = ALTER TYPE ... ADD VALUE (sans migration de tables).';

-- ----------------------------------------------------------------------------
-- 2) Fonctions utilitaires réutilisables
-- ----------------------------------------------------------------------------

-- Met à jour automatiquement updated_at. Réutilisable par TOUTE table future
-- possédant une colonne updated_at (architecture évolutive).
create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- Rôle de l'utilisateur courant, lu depuis le claim JWT `user_role`.
-- Tant que le Custom Access Token Hook n'injecte pas le claim (étape suivante),
-- retourne 'client' par défaut -> aucun accès privilégié accidentel.
-- Lecture du claim sans requête SQL -> pas de récursion RLS, performant (§5.2).
create or replace function public.current_user_role()
returns public.user_role
language sql
stable
set search_path = ''
as $$
  select coalesce(
    nullif(
      (nullif(current_setting('request.jwt.claims', true), '')::jsonb) ->> 'user_role',
      ''
    ),
    'client'
  )::public.user_role;
$$;

comment on function public.current_user_role() is
  'Rôle de l''appelant depuis le JWT (claim user_role). Défaut: client. Utilisé par les policies RLS.';

-- ----------------------------------------------------------------------------
-- 3) Table profiles (extension 1-1 de auth.users)
-- ----------------------------------------------------------------------------
create table public.profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  role       public.user_role not null default 'client',
  first_name text,                       -- nullable : complété à l'onboarding (cf. trigger)
  last_name  text,
  email      text,
  phone      text,
  avatar_url text,
  locale     text not null default 'fr',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.profiles is
  'Profil applicatif lié 1-1 à auth.users, créé automatiquement à l''inscription.';
comment on column public.profiles.role is
  'Rôle applicatif. Modifiable uniquement par un admin (garde-fou: trigger profiles_guard_role).';

-- updated_at automatique
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.handle_updated_at();

-- Anti-escalade de privilège : seul un admin peut modifier un rôle existant.
create or replace function public.profiles_guard_role()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_claims text := current_setting('request.jwt.claims', true);
begin
  -- Le rôle n'est verrouillé que pour un utilisateur final (requête avec JWT,
  -- non-admin, hors service_role). Les contextes serveur de confiance restent
  -- autorisés : admin applicatif, service_role, et SQL direct sans JWT
  -- (amorçage du premier admin, back-office, migrations).
  if new.role is distinct from old.role
     and public.current_user_role() <> 'admin'
     and nullif(v_claims, '') is not null
     and coalesce(v_claims::jsonb ->> 'role', '') <> 'service_role' then
    raise exception 'Modification du rôle non autorisée'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end;
$$;

create trigger profiles_guard_role
  before update on public.profiles
  for each row execute function public.profiles_guard_role();

-- ----------------------------------------------------------------------------
-- 4) Création automatique du profil à l'inscription
-- ----------------------------------------------------------------------------
-- SECURITY DEFINER : s'exécute avec les droits du propriétaire pour insérer
-- dans public.profiles au moment où GoTrue crée la ligne auth.users.
-- Le rôle n'est JAMAIS lu depuis raw_user_meta_data (contrôlé par l'utilisateur)
-- -> toujours 'client' par défaut (anti-escalade). L'élévation se fait ensuite
-- via un admin / service_role.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, phone, first_name, last_name, avatar_url, locale)
  values (
    new.id,
    new.email,
    new.phone,
    nullif(new.raw_user_meta_data ->> 'first_name', ''),
    nullif(new.raw_user_meta_data ->> 'last_name', ''),
    nullif(new.raw_user_meta_data ->> 'avatar_url', ''),
    coalesce(nullif(new.raw_user_meta_data ->> 'locale', ''), 'fr')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ----------------------------------------------------------------------------
-- 5) Row Level Security
-- ----------------------------------------------------------------------------
alter table public.profiles enable row level security;

-- Lecture : son propre profil.
create policy profiles_select_self on public.profiles
  for select to authenticated
  using (id = (select auth.uid()));

-- Mise à jour : son propre profil (le changement de rôle reste bloqué par trigger).
create policy profiles_update_self on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- Administration complète (select/insert/update/delete) réservée à l'admin.
-- Les policies permissives se cumulent en OU : un admin lit/écrit tout, un
-- utilisateur standard reste limité à son profil via les policies ci-dessus.
create policy profiles_admin_all on public.profiles
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

-- ----------------------------------------------------------------------------
-- 6) Privilèges Data API (PostgREST) — l'accès ligne à ligne est géré par la RLS
-- ----------------------------------------------------------------------------
grant select, insert, update, delete on public.profiles to authenticated;
