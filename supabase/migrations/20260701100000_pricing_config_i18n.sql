-- ============================================================================
-- M1.3 — Tarification, configuration & internationalisation
-- Réf. SPEC_FONCTIONNELLE_V1 §3/§4, DATA_MODEL §3.6/§3.8/§3.10, LEAN_V1 §1.1
--
-- Structure uniquement ; les valeurs de démo vivent dans supabase/seed.sql.
-- Tout est administrable (RLS admin) ; rien n'est codé en dur (P2).
-- Additif, compatible avec le différé (pricing_modifiers, config-versioning) — P10.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- app_config : source UNIQUE de configuration (seuils, délais, limites, flags).
-- value jsonb = booléen / nombre / chaîne / objet. scope limite l'exposition.
-- ----------------------------------------------------------------------------
create table public.app_config (
  key         text primary key,                       -- clé naturelle stable
  value       jsonb not null,
  scope       text not null default 'server'
                check (scope in ('public', 'server')), -- public = lisible par le client
  description text,
  is_active   boolean not null default true,
  updated_by  uuid references public.profiles(id) on delete set null,
  updated_at  timestamptz not null default now()
);

comment on table public.app_config is
  'Configuration clé/valeur (seuils, délais, limites, flags feature.*). Source unique.';
comment on column public.app_config.scope is
  'public = exposé au client ; server = réservé au serveur/admin.';

create trigger app_config_set_updated_at
  before update on public.app_config
  for each row execute function public.handle_updated_at();

alter table public.app_config enable row level security;

-- Lecture : clés publiques par tout authentifié ; admin voit tout.
create policy app_config_read on public.app_config
  for select to authenticated
  using (scope = 'public' or public.current_user_role() = 'admin');

-- Écriture : admin seul.
create policy app_config_admin_write on public.app_config
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.app_config to authenticated;

-- ----------------------------------------------------------------------------
-- content_strings : tous les textes affichés / i18n (source centralisée).
-- ----------------------------------------------------------------------------
create table public.content_strings (
  key         text not null,
  locale      text not null default 'fr',
  value       text not null,
  description text,
  is_active   boolean not null default true,
  updated_by  uuid references public.profiles(id) on delete set null,
  updated_at  timestamptz not null default now(),
  primary key (key, locale)
);
create index content_strings_key_idx on public.content_strings (key);

comment on table public.content_strings is
  'Textes affichés (labels, erreurs, mentions, copie de notifications) par locale.';

create trigger content_strings_set_updated_at
  before update on public.content_strings
  for each row execute function public.handle_updated_at();

alter table public.content_strings enable row level security;

create policy content_strings_read on public.content_strings
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');

create policy content_strings_admin_write on public.content_strings
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.content_strings to authenticated;

-- ----------------------------------------------------------------------------
-- pricing_rules : paramètres tarifaires par zone (zone_id NULL = défaut global).
-- currency par zone (prépare le multi-devise, cible). code = clé naturelle stable
-- pour le futur versionnement de configuration (P10).
-- ----------------------------------------------------------------------------
create table public.pricing_rules (
  id                        uuid primary key default gen_random_uuid(),
  code                      text unique,                 -- clé naturelle ('default'...)
  zone_id                   uuid references public.coverage_zones(id) on delete cascade,
  base_fare                 numeric(10,2) not null default 0   check (base_fare >= 0),
  price_per_km              numeric(10,2) not null default 0   check (price_per_km >= 0),
  minimum_price             numeric(10,2) not null default 0   check (minimum_price >= 0),
  authorization_margin_pct  numeric(5,2)  not null default 20  check (authorization_margin_pct >= 0),
  avg_speed_kmh             numeric(5,2)  not null default 25  check (avg_speed_kmh > 0),
  currency                  text          not null default 'eur',
  is_active                 boolean       not null default true,
  metadata                  jsonb         not null default '{}'::jsonb,
  created_at                timestamptz   not null default now(),
  updated_at                timestamptz   not null default now()
);

-- Au plus UNE règle active par zone (le défaut global = zone_id NULL).
create unique index pricing_rules_active_zone_uidx
  on public.pricing_rules (coalesce(zone_id, '00000000-0000-0000-0000-000000000000'::uuid))
  where is_active;

comment on table public.pricing_rules is
  'Paramètres tarifaires par zone (zone_id NULL = défaut global). Lus par estimate-price.';

create trigger pricing_rules_set_updated_at
  before update on public.pricing_rules
  for each row execute function public.handle_updated_at();

alter table public.pricing_rules enable row level security;

-- Lecture : tarifs actifs lisibles par tout authentifié ; admin voit tout.
create policy pricing_rules_read on public.pricing_rules
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');

create policy pricing_rules_admin_write on public.pricing_rules
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.pricing_rules to authenticated;
