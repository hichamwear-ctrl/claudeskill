-- ============================================================================
-- M4 — Fonctions serveur des missions (machine à états + revue + prix + zone)
-- Réf. API_SPEC §4/§5, BUSINESS_RULES §2, DATA_MODEL §3.13/§4.
--
-- Toutes SECURITY DEFINER (search_path figé) : elles sont l'UNIQUE écriture du
-- statut (RLS interdit l'UPDATE direct). Le graphe d'états est une ALLOW-LIST
-- EN CODE (mission_transitions différée — LEAN_V1 §1.2) ; les étapes optionnelles
-- (shopping/preparing) sont pilotées par la DONNÉE (category_workflow).
-- ============================================================================

-- Petit lecteur d'entier depuis app_config (jsonb nombre), avec défaut.
create or replace function public.config_int(p_key text, p_default int)
returns int
language sql
stable
set search_path = ''
as $$
  select coalesce(
    (select value::text::int from public.app_config where key = p_key and is_active),
    p_default
  );
$$;

-- ----------------------------------------------------------------------------
-- transition_mission : valide (from,to) + rôle + claim + workflow, applique le
--   changement de statut, les colonnes dérivées et journalise mission_events.
-- ----------------------------------------------------------------------------
create or replace function public.transition_mission(
  p_mission_id uuid,
  p_to         public.mission_status,
  p_reason     text    default null,
  p_price      numeric default null,
  p_eta_min    int     default null,
  p_metadata   jsonb   default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_role     public.user_role := public.current_user_role();
  v_uid      uuid := (select auth.uid());
  v_from     public.mission_status;
  v_client   uuid;
  v_operator uuid;
  v_category uuid;
  v_claim_by uuid;
  v_claim_at timestamptz;
  v_meta_qo  boolean;         -- catégorie « sur devis » (quote_only)
  v_allowed  public.user_role[];
  v_claim_ttl int := public.config_int('review.claim_ttl_min', 15);
  v_quote_h   int := public.config_int('quote_validity_hours', 24);
  v_is_review boolean := false;
begin
  select m.status, m.client_id, m.operator_id, m.category_id,
         m.review_claimed_by, m.review_claimed_at,
         coalesce((sc.metadata ->> 'quote_only')::boolean, false)
    into v_from, v_client, v_operator, v_category, v_claim_by, v_claim_at, v_meta_qo
  from public.missions m
  left join public.service_categories sc on sc.id = m.category_id
  where m.id = p_mission_id
  for update of m;

  if not found then
    raise exception 'mission introuvable' using errcode = 'no_data_found';
  end if;

  -- Allow-list (from, to) -> rôles autorisés. NULL = transition interdite.
  v_allowed := case
    -- Revue
    when v_from = 'pending_review'    and p_to = 'accepted'          then array['operator','admin']::public.user_role[]
    when v_from = 'pending_review'    and p_to = 'rejected'          then array['operator','admin']::public.user_role[]
    when v_from = 'pending_review'    and p_to = 'needs_information' then array['operator','admin']::public.user_role[]
    when v_from = 'needs_information' and p_to = 'pending_review'    then array['client','admin']::public.user_role[]
    -- Annulations avant acceptation (client)
    when v_from = 'pending_review'    and p_to = 'cancelled'         then array['client','admin']::public.user_role[]
    when v_from = 'needs_information' and p_to = 'cancelled'         then array['client','admin']::public.user_role[]
    -- Affectation & exécution
    when v_from = 'accepted'   and p_to = 'assigned'    then array['operator','admin']::public.user_role[]
    when v_from = 'accepted'   and p_to = 'cancelled'   then array['operator','admin']::public.user_role[]
    when v_from = 'assigned'   and p_to = 'shopping'    then array['operator','admin']::public.user_role[]
    when v_from = 'assigned'   and p_to = 'preparing'   then array['operator','admin']::public.user_role[]
    when v_from = 'assigned'   and p_to = 'en_route'    then array['operator','admin']::public.user_role[]
    when v_from = 'shopping'   and p_to = 'preparing'   then array['operator','admin']::public.user_role[]
    when v_from = 'shopping'   and p_to = 'en_route'    then array['operator','admin']::public.user_role[]
    when v_from = 'preparing'  and p_to = 'en_route'    then array['operator','admin']::public.user_role[]
    when v_from = 'en_route'   and p_to = 'arrived'     then array['operator','admin']::public.user_role[]
    when v_from = 'arrived'    and p_to = 'in_progress' then array['operator','admin']::public.user_role[]
    when v_from = 'in_progress' and p_to = 'completed'  then array['operator','admin']::public.user_role[]
    when v_from = 'completed'  and p_to = 'rated'       then array['client','admin']::public.user_role[]
    -- Échec d'exécution (intervenant)
    when v_from in ('assigned','shopping','preparing','en_route','arrived','in_progress')
         and p_to = 'failed'                            then array['operator','admin']::public.user_role[]
    when v_from in ('assigned','shopping','preparing','en_route','arrived','in_progress')
         and p_to = 'cancelled'                         then array['operator','admin']::public.user_role[]
    else null
  end;

  if v_allowed is null then
    raise exception 'transition interdite: % -> %', v_from, p_to using errcode = 'check_violation';
  end if;
  if not (v_role = any (v_allowed)) then
    raise exception 'rôle % non autorisé pour % -> %', v_role, v_from, p_to
      using errcode = 'insufficient_privilege';
  end if;

  -- Étapes optionnelles pilotées par category_workflow (données).
  if p_to in ('shopping', 'preparing')
     and not exists (
       select 1 from public.category_workflow w
       where w.category_id = v_category and w.status = p_to and w.is_active
     ) then
    raise exception 'étape % non activée pour cette catégorie', p_to using errcode = 'check_violation';
  end if;

  v_is_review := (v_from = 'pending_review' and p_to in ('accepted','rejected','needs_information'));

  -- Revue : exige un claim ACTIF de l'appelant (ou admin) — anti double-traitement.
  if v_is_review and v_role <> 'admin' then
    if v_claim_by is distinct from v_uid
       or v_claim_at is null
       or v_claim_at < now() - make_interval(mins => v_claim_ttl) then
      raise exception 'demande non prise en charge (claim requis)' using errcode = 'insufficient_privilege';
    end if;
  end if;

  -- Exécution : l'opérateur doit être l'intervenant affecté (sauf admin).
  if v_from in ('assigned','shopping','preparing','en_route','arrived','in_progress')
     and v_role = 'operator' and v_operator is distinct from v_uid then
    raise exception 'mission affectée à un autre intervenant' using errcode = 'insufficient_privilege';
  end if;

  -- Motif requis pour refus / demande d'infos.
  if p_to in ('rejected', 'needs_information') and coalesce(btrim(p_reason), '') = '' then
    raise exception 'motif requis' using errcode = 'not_null_violation';
  end if;

  -- Prix requis à l'acceptation d'une catégorie « sur devis ».
  if p_to = 'accepted' and v_meta_qo and p_price is null then
    raise exception 'prix requis (demande sur devis)' using errcode = 'not_null_violation';
  end if;

  -- Application du changement + colonnes dérivées.
  update public.missions m set
    status = p_to,
    operator_id = case
      when p_to = 'assigned' and m.operator_id is null and v_role = 'operator' then v_uid
      else m.operator_id end,
    reviewed_at   = case when v_is_review then now() else m.reviewed_at end,
    reviewed_by   = case when v_is_review then v_uid else m.reviewed_by end,
    review_reason = case when v_is_review then p_reason else m.review_reason end,
    accepted_at   = case when p_to = 'accepted' then now() else m.accepted_at end,
    quoted_price  = case when p_to = 'accepted' and p_price is not null then p_price else m.quoted_price end,
    quote_status  = case when p_to = 'accepted' and p_price is not null then 'accepted' else m.quote_status end,
    quote_expires_at = case when p_to = 'accepted' and p_price is not null
                            then now() + make_interval(hours => v_quote_h) else m.quote_expires_at end,
    estimated_eta_min = coalesce(case when p_to = 'accepted' then p_eta_min end, m.estimated_eta_min),
    completed_at  = case when p_to = 'completed' then now() else m.completed_at end,
    cancelled_at  = case when p_to in ('cancelled','failed') then now() else m.cancelled_at end,
    cancelled_by  = case when p_to in ('cancelled','failed') then v_role::text::public.cancel_actor else m.cancelled_by end,
    cancel_reason = case when p_to in ('cancelled','failed') then coalesce(p_reason, m.cancel_reason) else m.cancel_reason end
  where m.id = p_mission_id;

  insert into public.mission_events (mission_id, from_status, to_status, actor_id, actor_role, metadata)
  values (
    p_mission_id, v_from, p_to, v_uid, v_role,
    coalesce(p_metadata, '{}'::jsonb)
      || jsonb_strip_nulls(jsonb_build_object('reason', p_reason, 'price', p_price, 'eta_min', p_eta_min))
  );

  return jsonb_build_object('mission_id', p_mission_id, 'from_status', v_from, 'to_status', p_to);
end;
$$;

comment on function public.transition_mission is
  'Transition de statut validée (allow-list en code + rôle + claim + workflow). Unique écrivain du statut.';

-- ----------------------------------------------------------------------------
-- claim_review : prise en charge atomique d'une demande en revue (ou libération).
-- ----------------------------------------------------------------------------
create or replace function public.claim_review(
  p_mission_id uuid,
  p_release    boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_role     public.user_role := public.current_user_role();
  v_uid      uuid := (select auth.uid());
  v_status   public.mission_status;
  v_claim_by uuid;
  v_claim_at timestamptz;
  v_ttl      int := public.config_int('review.claim_ttl_min', 15);
begin
  if v_role not in ('operator', 'admin') then
    raise exception 'accès réservé aux opérateurs' using errcode = 'insufficient_privilege';
  end if;

  select status, review_claimed_by, review_claimed_at
    into v_status, v_claim_by, v_claim_at
  from public.missions where id = p_mission_id
  for update;

  if not found then
    raise exception 'mission introuvable' using errcode = 'no_data_found';
  end if;
  if v_status <> 'pending_review' then
    raise exception 'mission hors file de revue' using errcode = 'check_violation';
  end if;

  if p_release then
    if v_claim_by is distinct from v_uid and v_role <> 'admin' then
      raise exception 'claim détenu par un autre' using errcode = 'insufficient_privilege';
    end if;
    update public.missions set review_claimed_by = null, review_claimed_at = null
    where id = p_mission_id;
    return jsonb_build_object('mission_id', p_mission_id, 'claimed_by', null, 'claimed_at', null);
  end if;

  -- Claim actif détenu par un AUTRE (dans le TTL) -> conflit.
  if v_claim_by is not null and v_claim_by <> v_uid
     and v_claim_at is not null and v_claim_at >= now() - make_interval(mins => v_ttl)
     and v_role <> 'admin' then
    raise exception 'demande déjà prise en charge' using errcode = 'unique_violation';
  end if;

  update public.missions set review_claimed_by = v_uid, review_claimed_at = now()
  where id = p_mission_id;
  return jsonb_build_object('mission_id', p_mission_id, 'claimed_by', v_uid, 'claimed_at', now());
end;
$$;

comment on function public.claim_review is
  'Prise en charge atomique d''une demande en revue (verrou anti double-traitement, TTL app_config).';

-- ----------------------------------------------------------------------------
-- create_mission_from_conversation : matérialise une mission `pending_review`
--   à partir d'une conversation d'intake validée (clôture atomique). Serveur only.
-- ----------------------------------------------------------------------------
create or replace function public.create_mission_from_conversation(p_conversation_id uuid)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_client   uuid;
  v_status   public.conversation_status;
  v_state    jsonb;
  v_cls      text;
  v_cat      uuid;
  v_family   public.mission_family;
  v_mission  uuid;
begin
  select client_id, status, state into v_client, v_status, v_state
  from public.conversations where id = p_conversation_id
  for update;

  if not found then
    raise exception 'conversation introuvable' using errcode = 'no_data_found';
  end if;
  if v_status <> 'active' then
    raise exception 'conversation déjà close' using errcode = 'check_violation';
  end if;

  v_cls := v_state -> 'classification' ->> 0;              -- (garde-fou si tableau)
  v_cls := coalesce(nullif(v_state ->> 'classification', ''), v_cls);
  if v_cls is not null then
    select id, family into v_cat, v_family
    from public.service_categories where slug = v_cls and is_active;
  end if;

  insert into public.missions (
    client_id, category_id, family, status, conversation_id,
    details, metadata, dropoff_address, submitted_at
  ) values (
    v_client, v_cat, v_family, 'pending_review', p_conversation_id,
    coalesce(v_state -> 'answers', '{}'::jsonb),
    jsonb_strip_nulls(jsonb_build_object('classification', v_cls)),
    nullif(v_state -> 'answers' ->> 'address', ''),
    now()
  )
  returning id into v_mission;

  insert into public.mission_events (mission_id, from_status, to_status, actor_id, actor_role, metadata)
  values (v_mission, null, 'pending_review', v_client, 'client', jsonb_build_object('event', 'submit'));

  update public.conversations set status = 'submitted' where id = p_conversation_id;

  return v_mission;
end;
$$;

comment on function public.create_mission_from_conversation is
  'Clôture atomique d''une conversation validée -> mission pending_review + audit (serveur).';

-- ----------------------------------------------------------------------------
-- estimate_price : prix + ETA (pricing_rules par zone, base_fee catégorie).
--   Catégorie « sur devis » (metadata.quote_only) -> price null (fixé en revue).
-- ----------------------------------------------------------------------------
create or replace function public.estimate_price(
  p_category_id  uuid,
  p_dropoff_lng  double precision,
  p_dropoff_lat  double precision,
  p_pickup_lng   double precision default null,
  p_pickup_lat   double precision default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, extensions  -- types/fonctions PostGIS résolus dans extensions
as $$
declare
  v_dropoff   geography := ST_SetSRID(ST_MakePoint(p_dropoff_lng, p_dropoff_lat), 4326)::geography;
  v_pickup    geography := case when p_pickup_lng is not null and p_pickup_lat is not null
                            then ST_SetSRID(ST_MakePoint(p_pickup_lng, p_pickup_lat), 4326)::geography end;
  v_zone      uuid;
  v_rule      public.pricing_rules%rowtype;
  v_base_fee  numeric := 0;
  v_prep      int := 0;
  v_quote_only boolean := false;
  v_km        numeric := 0;
  v_distance_cost numeric := 0;
  v_price     numeric;
  v_eta       int;
begin
  select id into v_zone from public.coverage_zones
  where is_active and ST_Covers(area, v_dropoff) limit 1;

  select * into v_rule from public.pricing_rules
  where is_active and (zone_id = v_zone or (v_zone is null and zone_id is null))
  order by (zone_id is not null) desc limit 1;
  if not found then
    select * into v_rule from public.pricing_rules where is_active and zone_id is null limit 1;
  end if;
  if not found then
    raise exception 'aucune règle tarifaire' using errcode = 'no_data_found';
  end if;

  select coalesce(base_fee, 0), coalesce(prep_buffer_min, 0),
         coalesce((metadata ->> 'quote_only')::boolean, false)
    into v_base_fee, v_prep, v_quote_only
  from public.service_categories where id = p_category_id;

  if v_pickup is not null then
    v_km := ST_Distance(v_pickup, v_dropoff) / 1000.0;
  end if;
  v_distance_cost := round(v_km * v_rule.price_per_km, 2);
  v_eta := ceil(v_km / nullif(v_rule.avg_speed_kmh, 0) * 60)::int + v_prep;

  if v_quote_only then
    v_price := null;
  else
    v_price := greatest(v_rule.minimum_price, v_rule.base_fare + v_distance_cost) + v_base_fee;
  end if;

  return jsonb_build_object(
    'price', v_price,
    'eta_min', coalesce(v_eta, v_prep),
    'currency', v_rule.currency,
    'zone_id', v_zone,
    'quote_only', v_quote_only,
    'breakdown', jsonb_build_object(
      'base_fare', v_rule.base_fare,
      'distance_km', round(v_km, 3),
      'price_per_km', v_rule.price_per_km,
      'distance_cost', v_distance_cost,
      'minimum_price', v_rule.minimum_price,
      'category_base_fee', v_base_fee
    )
  );
end;
$$;

comment on function public.estimate_price is
  'Estimation prix + ETA (pricing_rules zone/défaut + base_fee catégorie). quote_only -> price null.';

-- ----------------------------------------------------------------------------
-- zone_check : couverture (ST_Covers) + ouverture (service_windows).
--   Fenêtres évaluées en heure locale (Europe/Brussels — V1 mono-ville).
-- ----------------------------------------------------------------------------
create or replace function public.zone_check(
  p_lng double precision,
  p_lat double precision,
  p_at  timestamptz default now()
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, extensions  -- types/fonctions PostGIS résolus dans extensions
as $$
declare
  v_tz    text := 'Europe/Brussels';
  v_point geography := ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography;
  v_zone  uuid;
  v_slug  text;
  v_local timestamptz;
  v_dow   int;
  v_time  time;
  v_open  boolean := false;
  v_next  jsonb := null;
begin
  select id, slug into v_zone, v_slug from public.coverage_zones
  where is_active and ST_Covers(area, v_point) limit 1;

  if v_zone is null then
    return jsonb_build_object('covered', false, 'zone_id', null, 'open', false, 'next_window', null);
  end if;

  v_local := p_at at time zone v_tz;
  v_dow := extract(dow from v_local)::int;
  v_time := v_local::time;

  select true into v_open from public.service_windows
  where zone_id = v_zone and is_active and weekday = v_dow
    and opens_at <= v_time and v_time < closes_at
  limit 1;
  v_open := coalesce(v_open, false);

  if not v_open then
    -- Prochaine ouverture (aujourd'hui plus tard, sinon prochain jour de la semaine).
    select jsonb_build_object('weekday', weekday, 'opens_at', opens_at, 'closes_at', closes_at)
      into v_next
    from public.service_windows
    where zone_id = v_zone and is_active
      and ( (weekday = v_dow and opens_at > v_time) or weekday <> v_dow )
    order by ((weekday - v_dow + 7) % 7), opens_at
    limit 1;
  end if;

  return jsonb_build_object(
    'covered', true, 'zone_id', v_zone, 'zone_slug', v_slug,
    'open', v_open, 'next_window', v_next
  );
end;
$$;

comment on function public.zone_check is
  'Couverture géographique (ST_Covers) + ouverture (service_windows, heure locale).';

-- ----------------------------------------------------------------------------
-- Privilèges d'exécution.
-- ----------------------------------------------------------------------------
grant execute on function public.config_int(text, int)                       to authenticated, service_role;
grant execute on function public.transition_mission(uuid, public.mission_status, text, numeric, int, jsonb) to authenticated, service_role;
grant execute on function public.claim_review(uuid, boolean)                 to authenticated, service_role;
grant execute on function public.create_mission_from_conversation(uuid)      to service_role;
grant execute on function public.estimate_price(uuid, double precision, double precision, double precision, double precision) to authenticated, service_role;
grant execute on function public.zone_check(double precision, double precision, timestamptz) to authenticated, service_role;
