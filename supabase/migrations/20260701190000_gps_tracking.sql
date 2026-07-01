-- ============================================================================
-- M7 — Localisation temps réel (suivi d'un intervenant PENDANT une mission)
-- Réf. GPS_TRACKING.md, DATA_MODEL §6, API_SPEC §7, BUSINESS_RULES (BR-GPS-*).
--
-- PRINCIPE : ce n'est PAS un historique GPS, PAS du fleet management, PAS de la
-- surveillance. Le suivi n'existe QUE pendant une mission active, uniquement pour
-- que le client suive son intervenant.
--
-- CHOIX LEAN (challengé) :
--   • Live haute fréquence  -> Realtime BROADCAST (aucune écriture DB par tick).
--   • Persistance V1        -> UNE table `operator_locations` (dernière position,
--     1 ligne/intervenant, upsert espacé) pour le repli (position périmée / reprise
--     d'app) et le futur dispatch « plus proche » (index GIST).
--   • `mission_tracks` (tracé échantillonné) : **DIFFÉRÉ** — c'est de l'historique/
--     preuve/analytics (hors périmètre V1) ; évite des centaines de milliers
--     d'écritures/jour. Ajout ultérieur sans refonte (consommateur du Broadcast).
--   • AUCUNE Edge Function : émission = RPC `update_location`, lecture = RPC
--     `get_operator_location`. Géofencing (proche/arrivée) = côté app (seuils en
--     app_config) — pas de trigger serveur (dropoff non géocodé en V1).
--
-- RGPD : jamais de position hors mission (garde en RPC + RLS) ; le client ne lit
-- que l'intervenant de SA mission active ; purge automatique à la clôture.
-- ============================================================================

-- États où le suivi est « armé/actif » (assigned → in_progress). Centralisé pour
-- éviter toute divergence (RLS, RPC, purge).
create or replace function public.is_tracking_state(s public.mission_status)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select s in ('assigned', 'shopping', 'preparing', 'en_route', 'arrived', 'in_progress');
$$;

-- ----------------------------------------------------------------------------
-- operator_locations : dernière position connue (1/intervenant). Upsert espacé.
-- ----------------------------------------------------------------------------
create table public.operator_locations (
  operator_id uuid primary key references public.profiles(id) on delete cascade,
  location    geography(point, 4326) not null,
  heading     numeric(5, 2),   -- cap 0..360°
  speed       numeric(6, 2),   -- m/s
  accuracy    numeric(7, 2),   -- mètres
  updated_at  timestamptz not null default now()
);
create index operator_locations_gix on public.operator_locations using gist (location);

comment on table public.operator_locations is
  'Dernière position d''un intervenant (repli + futur dispatch). Live = Broadcast, pas cette table.';

-- ----------------------------------------------------------------------------
-- RLS : l'intervenant écrit la SIENNE (via RPC) ; un client ne lit la position
-- que pour SA mission ACTIVE avec cet intervenant ; admin. Aucune lecture hors
-- mission active (vie privée). Aucune écriture directe (RPC SECURITY DEFINER).
-- ----------------------------------------------------------------------------
alter table public.operator_locations enable row level security;

create policy operator_locations_read on public.operator_locations
  for select to authenticated
  using (
    operator_id = (select auth.uid())
    or public.current_user_role() = 'admin'
    or exists (
      select 1 from public.missions m
      where m.operator_id = operator_locations.operator_id
        and m.client_id = (select auth.uid())
        and public.is_tracking_state(m.status)
    )
  );

grant select on public.operator_locations to authenticated;

-- ----------------------------------------------------------------------------
-- update_location : émission de la dernière position par l'intervenant.
--   Garde-fou VIE PRIVÉE : refusé s'il n'a AUCUNE mission active (pas de suivi
--   hors mission). Construit le point depuis lat/lng (aucune Edge Function).
-- ----------------------------------------------------------------------------
create or replace function public.update_location(
  p_lat      double precision,
  p_lng      double precision,
  p_heading  double precision default null,
  p_speed    double precision default null,
  p_accuracy double precision default null
)
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_uid uuid := (select auth.uid());
begin
  if public.current_user_role() <> 'operator' then
    raise exception 'réservé aux intervenants' using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.missions m
    where m.operator_id = v_uid and public.is_tracking_state(m.status)
  ) then
    raise exception 'aucune mission active (suivi interdit hors mission)' using errcode = 'check_violation';
  end if;

  insert into public.operator_locations (operator_id, location, heading, speed, accuracy, updated_at)
  values (
    v_uid, ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
    p_heading, p_speed, p_accuracy, now()
  )
  on conflict (operator_id) do update set
    location = excluded.location, heading = excluded.heading,
    speed = excluded.speed, accuracy = excluded.accuracy, updated_at = now();
end;
$$;

-- ----------------------------------------------------------------------------
-- get_operator_location : repli côté client (position périmée / reprise d'app).
--   Autorisé aux participants ; ne renvoie rien hors mission active (vie privée).
-- ----------------------------------------------------------------------------
create or replace function public.get_operator_location(p_mission_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, extensions
as $$
declare
  v_op     uuid;
  v_status public.mission_status;
  v_loc    public.operator_locations%rowtype;
  v_stale  int := public.config_int('gps.stale_after_sec', 30);
begin
  if not public.is_mission_participant(p_mission_id) then
    raise exception 'accès refusé' using errcode = 'insufficient_privilege';
  end if;
  select operator_id, status into v_op, v_status from public.missions where id = p_mission_id;
  if v_op is null or not public.is_tracking_state(v_status) then
    return null;   -- pas d'intervenant / mission non active -> aucune position
  end if;
  select * into v_loc from public.operator_locations where operator_id = v_op;
  if not found then
    return null;
  end if;
  return jsonb_build_object(
    'lat', ST_Y(v_loc.location::geometry),
    'lng', ST_X(v_loc.location::geometry),
    'heading', v_loc.heading, 'speed', v_loc.speed, 'accuracy', v_loc.accuracy,
    'updated_at', v_loc.updated_at,
    'stale', (now() - v_loc.updated_at) > make_interval(secs => v_stale)
  );
end;
$$;

-- ----------------------------------------------------------------------------
-- Purge RGPD : à la clôture de la DERNIÈRE mission active d'un intervenant, on
-- oublie sa position (aucune conservation inutile). Déclenché par la transition.
-- ----------------------------------------------------------------------------
create or replace function public.gps_forget_on_close()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status in ('completed', 'rated', 'cancelled', 'failed')
     and new.operator_id is not null
     and not exists (
       select 1 from public.missions m
       where m.operator_id = new.operator_id and m.id <> new.id
         and public.is_tracking_state(m.status)
     ) then
    delete from public.operator_locations where operator_id = new.operator_id;
  end if;
  return new;
end;
$$;

create trigger missions_gps_forget
  after update of status on public.missions
  for each row execute function public.gps_forget_on_close();

grant execute on function public.is_tracking_state(public.mission_status)                             to authenticated, service_role;
grant execute on function public.update_location(double precision, double precision, double precision, double precision, double precision) to authenticated, service_role;
grant execute on function public.get_operator_location(uuid)                                          to authenticated, service_role;
