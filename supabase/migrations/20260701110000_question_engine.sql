-- ============================================================================
-- M2.1 — Socle du moteur de questions (dialogue piloté par la donnée)
-- Réf. DATA_MODEL §3.11, CONVERSATION_ENGINE, LEAN_V1 §1.1
--
-- Le dialogue (quelles questions, dans quel ordre, sous quelles conditions) est
-- ENTIÈREMENT en données. Le moteur déterministe (M2.3) interprète ces tables.
-- Textes via content_strings (source unique). Additif, sans dette (P10).
-- ============================================================================

-- Types d'entrée (ensemble technique borné).
create type public.question_type as enum (
  'text', 'number', 'boolean', 'select', 'multiselect',
  'photo', 'document', 'address', 'date', 'time'
);

-- ----------------------------------------------------------------------------
-- question_sets : ensemble de questions.
--   category_id NULL = set GÉNÉRIQUE universel (P11 : parcours sans catégorie).
--   (capability_id sera ajouté additivement quand la couche capacités arrivera.)
-- ----------------------------------------------------------------------------
create table public.question_sets (
  id          uuid primary key default gen_random_uuid(),
  slug        text unique not null,                         -- clé naturelle stable
  name        text not null,
  category_id uuid references public.service_categories(id) on delete cascade,
  is_active   boolean not null default true,
  sort_order  int not null default 0,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index question_sets_category_idx on public.question_sets (category_id) where is_active;

comment on table public.question_sets is
  'Ensembles de questions. category_id NULL = set générique universel (P11).';

create trigger question_sets_set_updated_at
  before update on public.question_sets
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- questions : une question dynamique (slot).
--   label_key/help_key/placeholder_key -> content_strings (textes = source unique).
--   visible_when / required_when / validation : mini-langage borné (M2.3).
-- ----------------------------------------------------------------------------
create table public.questions (
  id              uuid primary key default gen_random_uuid(),
  set_id          uuid not null references public.question_sets(id) on delete cascade,
  key             text not null,                            -- stable (clé dans details/state)
  type            public.question_type not null,
  label_key       text not null,                            -- -> content_strings.key
  help_key        text,
  placeholder_key text,
  sort_order      int not null default 0,
  is_active       boolean not null default true,
  visible_when    jsonb not null default '{}'::jsonb,       -- {} = toujours visible
  required_when   jsonb not null default '{}'::jsonb,       -- {} = optionnel ; {"always":true} = requis
  validation      jsonb not null default '{}'::jsonb,       -- {min,max,maxLen,pattern,maxItems...}
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (set_id, key)
);
create index questions_set_idx on public.questions (set_id, sort_order) where is_active;

comment on table public.questions is
  'Questions dynamiques (slots). Ordre + conditions + validation en données.';

create trigger questions_set_updated_at
  before update on public.questions
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- question_options : options des questions select/multiselect.
-- ----------------------------------------------------------------------------
create table public.question_options (
  id          uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.questions(id) on delete cascade,
  value       text not null,
  label_key   text not null,                                -- -> content_strings.key
  sort_order  int not null default 0,
  is_active   boolean not null default true,
  metadata    jsonb not null default '{}'::jsonb,
  unique (question_id, value)
);
create index question_options_question_idx on public.question_options (question_id, sort_order) where is_active;

-- ----------------------------------------------------------------------------
-- RLS : lecture authentifiée (actifs ; admin voit tout) ; écriture admin.
-- (Config administrable & versionnable ; jamais codée en dur.)
-- ----------------------------------------------------------------------------
alter table public.question_sets    enable row level security;
alter table public.questions        enable row level security;
alter table public.question_options enable row level security;

create policy question_sets_read on public.question_sets
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy question_sets_admin_write on public.question_sets
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

create policy questions_read on public.questions
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy questions_admin_write on public.questions
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

create policy question_options_read on public.question_options
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy question_options_admin_write on public.question_options
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

grant select, insert, update, delete on public.question_sets    to authenticated;
grant select, insert, update, delete on public.questions        to authenticated;
grant select, insert, update, delete on public.question_options to authenticated;
