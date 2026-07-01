-- ============================================================================
-- M1.2 — Zones de couverture & horaires de service
-- Réf. Architecture §6.3 + SPEC_FONCTIONNELLE_V1 (zones configurables sans code)
--
-- Structure uniquement ; la zone de démo vit dans supabase/seed.sql.
-- Une ville = une ligne coverage_zones : ajouter une ville n'exige AUCUN code.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- coverage_zones : masque géographique (PostGIS).
-- ----------------------------------------------------------------------------
create table public.coverage_zones (
  id         uuid primary key default gen_random_uuid(),
  slug       text unique,                          -- réf stable ('brussels'...)
  name       text not null,
  area       geography(polygon, 4326) not null,    -- polygone de couverture
  is_active  boolean not null default true,
  metadata   jsonb not null default '{}'::jsonb,   -- extension future sans migration
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index coverage_zones_gix on public.coverage_zones using gist (area);

comment on table public.coverage_zones is
  'Zones couvertes (PostGIS). Une ville = une ligne ; administrable, aucun code.';

create trigger coverage_zones_set_updated_at
  before update on public.coverage_zones
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- service_windows : créneaux d'ouverture par zone et par jour.
-- Créneau de nuit (ex. 22:00->02:00) = représenté par DEUX lignes.
-- ----------------------------------------------------------------------------
create table public.service_windows (
  id         uuid primary key default gen_random_uuid(),
  zone_id    uuid not null references public.coverage_zones(id) on delete cascade,
  weekday    smallint not null check (weekday between 0 and 6),  -- 0=dimanche .. 6=samedi
  opens_at   time not null,
  closes_at  time not null,
  is_active  boolean not null default true,
  created_at timestamptz not null default now(),
  constraint service_windows_range check (opens_at < closes_at)
);
create index service_windows_zone_idx on public.service_windows (zone_id, weekday) where is_active;

-- ----------------------------------------------------------------------------
-- waitlist : demande latente hors zone.
-- ----------------------------------------------------------------------------
create table public.waitlist (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references public.profiles(id) on delete set null,
  email      text,
  phone      text,
  location   geography(point, 4326),
  note       text,
  created_at timestamptz not null default now()
);
create index waitlist_created_idx on public.waitlist (created_at desc);

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------
alter table public.coverage_zones  enable row level security;
alter table public.service_windows enable row level security;
alter table public.waitlist        enable row level security;

-- Zones : lecture authentifiée (actives ; admin voit tout), écriture admin.
create policy coverage_zones_read on public.coverage_zones
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy coverage_zones_admin_write on public.coverage_zones
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

-- Horaires : lecture authentifiée (actifs ; admin voit tout), écriture admin.
create policy service_windows_read on public.service_windows
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy service_windows_admin_write on public.service_windows
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

-- Waitlist : l'utilisateur s'inscrit (insert), seul l'admin lit.
create policy waitlist_self_insert on public.waitlist
  for insert to authenticated
  with check (user_id = (select auth.uid()) or user_id is null);
create policy waitlist_admin_read on public.waitlist
  for select to authenticated
  using (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.coverage_zones  to authenticated;
grant select, insert, update, delete on public.service_windows to authenticated;
grant select, insert                 on public.waitlist        to authenticated;
