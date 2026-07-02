-- ============================================================================
-- M10 — Cockpit opérateur/admin + validation de configuration
-- Réf. ADMIN_PANEL (AD-02/AD-04/AD-15), API_SPEC, DATA_MODEL.
--
-- RPC SECURITY DEFINER (autorisation vérifiée EN INTERNE) : elles consolident les
-- lectures pour éviter le N+1 côté front, tout en lisant des tables protégées par
-- RLS (profiles, payments…) après contrôle du rôle. Aucune vue security_invoker :
-- une jointure sur `profiles` (RLS = self) masquerait le nom du client.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- validate_config : rapport de cohérence de la configuration (lecture seule).
--   Détecte références cassées / clés i18n absentes / orphelins / incohérences.
--   Admin uniquement. « Une erreur claire plutôt qu'une donnée incohérente. »
-- ----------------------------------------------------------------------------
create or replace function public.validate_config()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if public.current_user_role() <> 'admin' then
    raise exception 'réservé à l''administration' using errcode = 'insufficient_privilege';
  end if;

  return (
    select coalesce(jsonb_agg(to_jsonb(i)), '[]'::jsonb) from (
      -- Libellés de questions sans content_strings
      select 'error' as severity, 'question_label_missing' as kind,
             s.slug || '.' || q.key as ref, q.label_key as detail
      from public.questions q join public.question_sets s on s.id = q.set_id
      where q.is_active and not exists (
        select 1 from public.content_strings cs where cs.key = q.label_key and cs.is_active)
      union all
      -- Options sans content_strings
      select 'error', 'option_label_missing', q.key || '=' || o.value, o.label_key
      from public.question_options o join public.questions q on q.id = o.question_id
      where o.is_active and not exists (
        select 1 from public.content_strings cs where cs.key = o.label_key and cs.is_active)
      union all
      -- select/multiselect sans aucune option active
      select 'error', 'select_without_options', q.key, q.type::text
      from public.questions q
      where q.is_active and q.type in ('select', 'multiselect') and not exists (
        select 1 from public.question_options o where o.question_id = q.id and o.is_active)
      union all
      -- Templates de notification référençant des textes absents
      select 'error', 'template_string_missing', t.key || '/' || t.audience,
             coalesce(k.key_val, '')
      from public.notification_templates t
      cross join lateral (values (t.title_key), (t.body_key)) as k(key_val)
      where t.is_active and k.key_val is not null and not exists (
        select 1 from public.content_strings cs where cs.key = k.key_val and cs.is_active)
      union all
      -- Déclencheurs sans template actif correspondant
      select 'error', 'trigger_without_template', tr.event_key || '→' || tr.template_key,
             tr.audience
      from public.notification_triggers tr
      where tr.is_active and not exists (
        select 1 from public.notification_templates tpl
        where tpl.key = tr.template_key and tpl.audience = tr.audience and tpl.is_active)
      union all
      -- Aucune règle tarifaire par défaut active
      select 'error', 'pricing_default_missing', 'pricing_rules', 'zone_id is null'
      where not exists (
        select 1 from public.pricing_rules where zone_id is null and is_active)
    ) i
  );
end;
$$;

comment on function public.validate_config is
  'Rapport de cohérence de la configuration (références/i18n/orphelins/tarifs). Admin.';

-- ----------------------------------------------------------------------------
-- operator_queue : file de revue enrichie, visible selon le claim (op/admin).
-- ----------------------------------------------------------------------------
create or replace function public.operator_queue()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_role public.user_role := public.current_user_role();
  v_uid  uuid := (select auth.uid());
begin
  if v_role not in ('operator', 'admin') then
    raise exception 'réservé aux opérateurs' using errcode = 'insufficient_privilege';
  end if;
  return (
    select coalesce(jsonb_agg(to_jsonb(q) order by q.submitted_at), '[]'::jsonb)
    from (
      select m.id as mission_id, m.status, m.submitted_at,
             m.review_claimed_by, m.review_claimed_at, m.client_id,
             p.first_name as client_name,
             sc.slug as category_slug, sc.label as category_label,
             left(coalesce(m.free_text, m.details ->> 'details'), 200) as summary
      from public.missions m
      left join public.profiles p on p.id = m.client_id
      left join public.service_categories sc on sc.id = m.category_id
      where m.status = 'pending_review'
        and (v_role = 'admin' or m.review_claimed_by is null or m.review_claimed_by = v_uid)
    ) q
  );
end;
$$;

-- ----------------------------------------------------------------------------
-- mission_overview : détail consolidé d'une mission (1 appel pour l'écran détail).
--   Autorisation = miroir de la RLS missions (client/opérateur affecté/file/admin).
-- ----------------------------------------------------------------------------
create or replace function public.mission_overview(p_mission_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  m      public.missions%rowtype;
  v_role public.user_role := public.current_user_role();
  v_uid  uuid := (select auth.uid());
begin
  select * into m from public.missions where id = p_mission_id;
  if not found then
    raise exception 'mission introuvable' using errcode = 'no_data_found';
  end if;
  -- coalesce(...,false) : `operator_id = v_uid` vaut NULL si operator_id IS NULL ;
  -- sans coalesce, NOT NULL = NULL et la garde ne se déclencherait pas (faille).
  if not coalesce(
    m.client_id = v_uid
    or (m.operator_id is not null and m.operator_id = v_uid)
    or v_role = 'admin'
    or (v_role = 'operator' and m.status = 'pending_review'
        and (m.review_claimed_by is null or m.review_claimed_by = v_uid)),
    false
  ) then
    raise exception 'accès refusé' using errcode = 'insufficient_privilege';
  end if;

  return jsonb_build_object(
    'mission', jsonb_build_object(
      'id', m.id, 'status', m.status, 'client_id', m.client_id, 'operator_id', m.operator_id,
      'category_id', m.category_id, 'dropoff_address', m.dropoff_address,
      'details', m.details, 'quoted_price', m.quoted_price, 'final_amount', m.final_amount,
      'review_claimed_by', m.review_claimed_by, 'reviewed_by', m.reviewed_by,
      'review_reason', m.review_reason, 'submitted_at', m.submitted_at,
      'accepted_at', m.accepted_at, 'completed_at', m.completed_at, 'created_at', m.created_at
    ),
    'payment', (select to_jsonb(p) from public.payments p where p.mission_id = m.id),
    'events', (
      select coalesce(jsonb_agg(to_jsonb(e) order by e.created_at), '[]'::jsonb)
      from public.mission_events e where e.mission_id = m.id
    ),
    'conversation', (
      select jsonb_build_object('id', c.id, 'status', c.status)
      from public.conversations c where c.id = m.conversation_id
    ),
    'unread_messages', (
      select count(*) from public.messages msg
      where msg.mission_id = m.id and msg.read_at is null
    )
  );
end;
$$;

-- ----------------------------------------------------------------------------
-- admin_stats : indicateurs de pilotage (tableau de bord). Admin uniquement.
-- ----------------------------------------------------------------------------
create or replace function public.admin_stats()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if public.current_user_role() <> 'admin' then
    raise exception 'réservé à l''administration' using errcode = 'insufficient_privilege';
  end if;
  return jsonb_build_object(
    'missions_by_status', (
      select coalesce(jsonb_object_agg(status, c), '{}'::jsonb)
      from (select status::text, count(*) c from public.missions group by status) s
    ),
    'review_queue', (select count(*) from public.missions where status = 'pending_review'),
    'review_claimed', (
      select count(*) from public.missions
      where status = 'pending_review' and review_claimed_by is not null
    ),
    'active_conversations', (select count(*) from public.conversations where status = 'active'),
    'payments_by_status', (
      select coalesce(jsonb_object_agg(status, c), '{}'::jsonb)
      from (select status::text, count(*) c from public.payments group by status) p
    ),
    'unread_notifications', (select count(*) from public.notifications where read_at is null)
  );
end;
$$;

grant execute on function public.validate_config()          to authenticated, service_role;
grant execute on function public.operator_queue()           to authenticated, service_role;
grant execute on function public.mission_overview(uuid)     to authenticated, service_role;
grant execute on function public.admin_stats()              to authenticated, service_role;
