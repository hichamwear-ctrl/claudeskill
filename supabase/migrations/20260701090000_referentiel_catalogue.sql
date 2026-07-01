-- ============================================================================
-- M1.1 — Référentiel : catalogue de services (administrable)
-- Réf. Architecture §6.3 + SPEC_FONCTIONNELLE_V1 §1
--
-- Structure uniquement (les données de démo vivent dans supabase/seed.sql).
-- Le catalogue est 100 % administrable : aucune catégorie n'est codée en dur.
-- ============================================================================

-- Famille de mission (enum métier). Évolutif : ALTER TYPE ... ADD VALUE.
create type public.mission_family as enum ('shopping', 'auto', 'home_service', 'courier', 'custom');

comment on type public.mission_family is
  'Familles de services. Évolutif : ajouter une famille = ALTER TYPE ... ADD VALUE.';

-- Catalogue des services.
create table public.service_categories (
  id                   uuid primary key default gen_random_uuid(),
  family               public.mission_family not null,
  slug                 text unique not null,                 -- identifiant stable ('groceries'...)
  label                text not null,                        -- libellé affiché (éditable)
  icon                 text,                                 -- nom d'icône (éditable)
  is_active            boolean not null default true,        -- activer/désactiver sans suppression
  fulfillment          text not null default 'self'
                         check (fulfillment in ('self', 'partner')),
  legal_note           text,                                 -- mention légale affichée
  base_fee             numeric(10, 2) not null default 0     -- supplément tarifaire catégorie
                         check (base_fee >= 0),
  prep_buffer_min      int not null default 0                -- délai additionnel (ETA)
                         check (prep_buffer_min >= 0),
  requires_shopping    boolean not null default false,       -- passe par l'état `shopping`
  requires_preparation boolean not null default false,       -- passe par l'état `preparing`
  sort_order           int not null default 0,               -- ordre d'affichage
  metadata             jsonb not null default '{}'::jsonb,   -- extension future SANS migration
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index service_categories_family_idx on public.service_categories (family) where is_active;
create index service_categories_sort_idx   on public.service_categories (sort_order);

comment on table public.service_categories is
  'Catalogue administrable. Structure en migration ; données via seed / panneau admin.';
comment on column public.service_categories.metadata is
  'Attributs additionnels libres (évolutivité sans migration de schéma).';

-- updated_at automatique (fonction réutilisable créée au socle identité).
create trigger service_categories_set_updated_at
  before update on public.service_categories
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- RLS : lecture authentifiée (actives ; admin voit tout) ; écriture admin seule.
-- ----------------------------------------------------------------------------
alter table public.service_categories enable row level security;

create policy service_categories_read on public.service_categories
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');

create policy service_categories_admin_write on public.service_categories
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.service_categories to authenticated;
