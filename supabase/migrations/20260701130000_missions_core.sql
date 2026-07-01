-- ============================================================================
-- M4 — Cœur missions : cycle de vie, workflow, audit
-- Réf. DATA_MODEL §3.2/§4.1/§4.3, BUSINESS_RULES §2, LEAN_V1 §1.1/§1.2/§3
--
-- La MISSION est l'objet central (machine à états, source de vérité). En V1 :
--   • machine à états = ALLOW-LIST EN CODE (RPC transition_mission, migration
--     suivante) ; la table `mission_transitions` (édition du graphe) reste
--     DIFFÉRÉE (LEAN_V1 §1.2) ;
--   • colonnes ABSORBANT des tables différées (LEAN_V1 §1.1) : quote_* (quotes),
--     advance_* (advances), tip_amount (tips), details jsonb (mission_items) ;
--   • `category_workflow` (V1) généralise requires_shopping/requires_preparation,
--     désormais RETIRÉS de service_categories (aucune dépendance — DATA_MODEL §3.1).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Enums du cycle de vie.
-- mission_status : liste CIBLE complète (DATA_MODEL §9) — créer tout de suite
--   évite des ALTER TYPE ultérieurs. `searching` réservé (multi-opérateur).
-- ----------------------------------------------------------------------------
create type public.mission_status as enum (
  'created', 'pending_review', 'needs_information', 'rejected',
  'accepted', 'assigned', 'searching',
  'shopping', 'preparing', 'en_route', 'arrived', 'in_progress',
  'completed', 'rated', 'cancelled', 'failed'
);
comment on type public.mission_status is
  'Cycle de vie des missions (cible complète). Transitions = allow-list en code (V1).';

create type public.cancel_actor as enum ('client', 'operator', 'admin', 'system');

-- ----------------------------------------------------------------------------
-- Évolution service_categories : les étapes optionnelles passent en données
-- (category_workflow). On retire les 2 booléens (aucune donnée métier ne s'y
-- réfère encore — seul le seed les posait, mis à jour en parallèle).
-- ----------------------------------------------------------------------------
alter table public.service_categories drop column if exists requires_shopping;
alter table public.service_categories drop column if exists requires_preparation;

-- ----------------------------------------------------------------------------
-- category_workflow : étapes d'exécution optionnelles activées par catégorie.
--   Ajouter une étape future (ex. quality_check) = INSÉRER une ligne, aucun code.
--   `status` ∈ étapes optionnelles (shopping/preparing/…) — jamais les états pivots.
-- ----------------------------------------------------------------------------
create table public.category_workflow (
  id             uuid primary key default gen_random_uuid(),
  category_id    uuid not null references public.service_categories(id) on delete cascade,
  status         public.mission_status not null
                   check (status in ('shopping', 'preparing')),  -- étapes optionnelles V1
  sort_order     int not null default 0,
  requires_proof boolean not null default false,
  is_active      boolean not null default true,
  unique (category_id, status)
);
create index category_workflow_cat_idx on public.category_workflow (category_id, sort_order)
  where is_active;

comment on table public.category_workflow is
  'Étapes d''exécution optionnelles par catégorie (généralise requires_shopping/preparation).';

-- ----------------------------------------------------------------------------
-- missions : objet central. Colonnes larges (absorption V1) ; details/metadata
--   jsonb pour l'évolutivité sans migration. Le STATUT n'est jamais mis à jour
--   directement (RLS) : il passe par transition_mission (SECURITY DEFINER).
-- ----------------------------------------------------------------------------
create table public.missions (
  id                    uuid primary key default gen_random_uuid(),
  -- identité / acteurs
  client_id             uuid not null references public.profiles(id) on delete restrict,
  operator_id           uuid references public.profiles(id) on delete set null,
  category_id           uuid references public.service_categories(id) on delete set null,
  family                public.mission_family,
  status                public.mission_status not null default 'created',
  -- origine conversationnelle (CONVERSATION_ENGINE §7)
  conversation_id       uuid references public.conversations(id) on delete set null,
  group_id              uuid,
  sequence              int,
  depends_on_mission_id uuid references public.missions(id) on delete set null,
  -- contenu
  title                 text,
  free_text             text,
  instructions          text,
  details               jsonb not null default '{}'::jsonb,  -- réponses (slots remplis)
  metadata              jsonb not null default '{}'::jsonb,  -- dont classification
  -- localisation
  dropoff_address       text,
  dropoff_point         geography(point, 4326),
  pickup_point          geography(point, 4326),
  -- tarif (snapshots) + absorptions (quotes/advances/tips)
  estimated_price       numeric(10, 2),
  estimated_eta_min     int,
  service_fee           numeric(10, 2),
  advance_estimate      numeric(10, 2),
  advance_actual        numeric(10, 2),
  final_amount          numeric(10, 2),
  operator_earning      numeric(10, 2),
  quoted_price          numeric(10, 2),
  quote_expires_at      timestamptz,
  quote_status          text check (quote_status in ('proposed', 'accepted', 'expired', 'cancelled')),
  tip_amount            numeric(10, 2),
  -- revue (claim + décision)
  submitted_at          timestamptz,
  review_claimed_by     uuid references public.profiles(id) on delete set null,
  review_claimed_at     timestamptz,
  reviewed_at           timestamptz,
  reviewed_by           uuid references public.profiles(id) on delete set null,
  review_reason         text,
  -- cycle
  accepted_at           timestamptz,
  completed_at          timestamptz,
  cancelled_at          timestamptz,
  cancelled_by          public.cancel_actor,
  cancel_reason         text,
  scheduled_for         timestamptz,
  queue_position        int,
  -- timestamps
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index missions_client_idx       on public.missions (client_id, created_at desc);
create index missions_operator_idx     on public.missions (operator_id) where operator_id is not null;
create index missions_status_idx       on public.missions (status);
create index missions_review_queue_idx on public.missions (submitted_at) where status = 'pending_review';
create index missions_conversation_idx on public.missions (conversation_id);
create index missions_group_idx        on public.missions (group_id) where group_id is not null;
create index missions_dropoff_gix      on public.missions using gist (dropoff_point);

comment on table public.missions is
  'Objet central (machine à états). Statut modifié uniquement via transition_mission.';

create trigger missions_set_updated_at
  before update on public.missions
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- mission_events : journal IMMUABLE des transitions (audit — BR-224).
--   Écrit uniquement par transition_mission / create_mission_from_conversation.
-- ----------------------------------------------------------------------------
create table public.mission_events (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references public.missions(id) on delete cascade,
  from_status public.mission_status,
  to_status   public.mission_status not null,
  actor_id    uuid references public.profiles(id) on delete set null,
  actor_role  public.user_role,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index mission_events_mission_idx on public.mission_events (mission_id, created_at);

comment on table public.mission_events is
  'Audit immuable des transitions de mission. Écriture via fonctions SECURITY DEFINER.';

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------
alter table public.category_workflow enable row level security;
alter table public.missions          enable row level security;
alter table public.mission_events    enable row level security;

-- category_workflow : lecture authentifiée (actif ; admin voit tout), écriture admin.
create policy category_workflow_read on public.category_workflow
  for select to authenticated
  using (is_active or public.current_user_role() = 'admin');
create policy category_workflow_admin_write on public.category_workflow
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

-- missions : le client voit les siennes ; l'opérateur voit les siennes ET la file
--   de revue `pending_review` NON claimée ou claimée par lui (vie privée + anti
--   double-traitement) ; l'admin voit tout. AUCUNE écriture directe (statut via RPC).
create policy missions_read on public.missions
  for select to authenticated
  using (
    client_id = (select auth.uid())
    or operator_id = (select auth.uid())
    or (
      public.current_user_role() = 'operator'
      and status = 'pending_review'
      and (review_claimed_by is null or review_claimed_by = (select auth.uid()))
    )
    or public.current_user_role() = 'admin'
  );

-- mission_events : participants de la mission + admin (lecture seule).
create policy mission_events_read on public.mission_events
  for select to authenticated
  using (
    exists (
      select 1 from public.missions m
      where m.id = mission_events.mission_id
        and (
          m.client_id = (select auth.uid())
          or m.operator_id = (select auth.uid())
          or public.current_user_role() = 'admin'
        )
    )
  );

-- Lecture pour l'app ; écritures via fonctions SECURITY DEFINER / service_role.
grant select on public.missions       to authenticated;
grant select on public.mission_events to authenticated;
grant select, insert, update, delete on public.category_workflow to authenticated;
