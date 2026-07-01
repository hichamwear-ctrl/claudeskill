-- ============================================================================
-- M8 — Résolution & écriture des notifications (data-driven, idempotent)
-- Réf. NOTIFICATIONS.md §2/§7/§8, API_SPEC §4.9.
--
-- `dispatch_notifications` fait TOUTE la résolution data-driven en base
-- (triggers → templates → content_strings → notifications) et renvoie la liste à
-- POUSSER. L'Edge `send-push` n'est qu'un TRANSPORT (aucune logique métier).
-- Idempotence = contrainte UNIQUE `notifications.dedup_key`. Textes = uniquement
-- `content_strings`. Silence nocturne + min_interval = `app_config.notifications.*`.
-- ============================================================================

-- Rend un gabarit en remplaçant {clé} par la valeur du contexte (déterministe).
create or replace function public.render_template(p_tpl text, p_ctx jsonb)
returns text
language plpgsql
immutable
set search_path = ''
as $$
declare
  v text := p_tpl;
  k text;
begin
  if v is null then return null; end if;
  for k in select jsonb_object_keys(p_ctx) loop
    v := replace(v, '{' || k || '}', coalesce(p_ctx ->> k, ''));
  end loop;
  return v;
end;
$$;

-- ----------------------------------------------------------------------------
-- dispatch_notifications : résout un événement en notifications idempotentes.
--   Renvoie { dispatched, push: [{ notification_id, user_id, title, body,
--   deep_link, payload, tokens[] }] }. Serveur uniquement.
-- ----------------------------------------------------------------------------
create or replace function public.dispatch_notifications(p_event_key text, p_context jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_tz          text := 'Europe/Brussels';
  v_quiet       jsonb := (select value from public.app_config
                          where key = 'notifications.quiet_hours' and is_active);
  v_min_interval int := public.config_int('notifications.min_interval_sec', 60);
  v_now_time    time := (now() at time zone v_tz)::time;
  v_from        time := nullif(v_quiet ->> 'from', '')::time;
  v_to          time := nullif(v_quiet ->> 'to', '')::time;
  v_in_quiet    boolean := case
                  when v_quiet is null then false
                  when v_from < v_to then v_now_time >= v_from and v_now_time < v_to
                  else v_now_time >= v_from or v_now_time < v_to end;
  v_mission     public.missions%rowtype;
  v_sender      uuid := nullif(p_context ->> 'sender_id', '')::uuid;
  v_dispatched  int := 0;
  v_push        jsonb := '[]'::jsonb;
  t             record;
  tpl           public.notification_templates%rowtype;
  v_recipients  uuid[];
  v_uid         uuid;
  v_loc         text;
  v_title_s     text;
  v_body_s      text;
  v_title       text;
  v_body        text;
  v_deep        text;
  v_dedup       text;
  v_bypass      boolean;
  v_do_push     boolean;
  v_recent      boolean;
  v_nid         uuid;
  v_tokens      jsonb;
begin
  if p_context ? 'mission_id' then
    select * into v_mission from public.missions where id = (p_context ->> 'mission_id')::uuid;
  end if;

  for t in
    select * from public.notification_triggers
    where event_key = p_event_key and is_active
    order by sort_order, template_key
  loop
    -- Condition bornée : {} = toujours ; {"context_eq":{k:v,...}} ; sinon fail-closed.
    if t.condition is not null and t.condition <> '{}'::jsonb then
      if t.condition ? 'context_eq' then
        if exists (
          select 1 from jsonb_each_text(t.condition -> 'context_eq') kv
          where coalesce(p_context ->> kv.key, '') <> kv.value
        ) then continue; end if;
      else
        continue;  -- opérateur de condition inconnu -> on n'envoie pas
      end if;
    end if;

    -- Template ACTIF correspondant (absence -> skip gracieux).
    select * into tpl from public.notification_templates
    where key = t.template_key and audience = t.audience and is_active;
    if not found then continue; end if;

    -- Destinataires selon l'audience (override explicite user_id possible).
    if p_context ? 'user_id' then
      v_recipients := array[(p_context ->> 'user_id')::uuid];
    elsif t.audience = 'client' then
      v_recipients := array[v_mission.client_id];
    elsif t.audience = 'operator' then
      v_recipients := array[v_mission.operator_id];
    else  -- admin
      v_recipients := (select coalesce(array_agg(id), '{}') from public.profiles where role = 'admin');
    end if;

    foreach v_uid in array v_recipients loop
      if v_uid is null or v_uid = v_sender then continue; end if;  -- pas d'auto-notification

      v_loc := coalesce((select locale from public.profiles where id = v_uid), 'fr');
      v_title_s := (select value from public.content_strings
                    where key = tpl.title_key and locale = v_loc and is_active);
      if v_title_s is null then
        v_title_s := (select value from public.content_strings
                      where key = tpl.title_key and locale = 'fr' and is_active);
      end if;
      if v_title_s is null then continue; end if;  -- content_strings absent -> skip gracieux

      v_body_s := (select value from public.content_strings
                   where key = tpl.body_key and locale = v_loc and is_active);
      if v_body_s is null and tpl.body_key is not null then
        v_body_s := (select value from public.content_strings
                     where key = tpl.body_key and locale = 'fr' and is_active);
      end if;

      v_title := public.render_template(v_title_s, p_context);
      v_body  := public.render_template(v_body_s, p_context);
      v_deep  := public.render_template(tpl.deep_link_template, p_context);
      v_dedup := coalesce(p_context ->> 'source_ref', p_event_key)
                 || ':' || tpl.key || ':' || tpl.audience || ':' || v_uid::text;

      v_bypass := coalesce((tpl.metadata ->> 'bypass_quiet_hours')::boolean, false);
      v_recent := exists (
        select 1 from public.notifications n
        where n.user_id = v_uid and n.template = tpl.key
          and n.created_at > now() - make_interval(secs => v_min_interval)
      );
      v_do_push := tpl.channel in ('push', 'both')
                   and not (v_in_quiet and not v_bypass)   -- silence nocturne (sauf bypass)
                   and not v_recent;                        -- anti-spam (min_interval)

      insert into public.notifications
        (user_id, template, channel, title, body, deep_link, payload, mission_id, dedup_key, pushed)
      values (v_uid, tpl.key, tpl.channel, v_title, v_body, v_deep, p_context,
              (p_context ->> 'mission_id')::uuid, v_dedup, v_do_push)
      on conflict (dedup_key) do nothing
      returning id into v_nid;

      if v_nid is not null then
        v_dispatched := v_dispatched + 1;
        if v_do_push then
          v_tokens := (select coalesce(jsonb_agg(token), '[]'::jsonb)
                       from public.device_tokens where user_id = v_uid and active);
          v_push := v_push || jsonb_build_object(
            'notification_id', v_nid, 'user_id', v_uid, 'title', v_title, 'body', v_body,
            'deep_link', v_deep, 'payload', p_context, 'tokens', v_tokens);
        end if;
      end if;
    end loop;
  end loop;

  return jsonb_build_object('dispatched', v_dispatched, 'push', v_push);
end;
$$;

comment on function public.dispatch_notifications is
  'Résout un événement en notifications idempotentes (data-driven) et renvoie la liste à pousser.';

-- ----------------------------------------------------------------------------
-- Accusés de lecture (destinataire uniquement).
-- ----------------------------------------------------------------------------
create or replace function public.mark_notification_read(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.notifications set read_at = now()
  where id = p_id and user_id = (select auth.uid()) and read_at is null;
end;
$$;

create or replace function public.mark_all_notifications_read()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  update public.notifications set read_at = now()
  where user_id = (select auth.uid()) and read_at is null;
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

grant execute on function public.render_template(text, jsonb)           to authenticated, service_role;
grant execute on function public.dispatch_notifications(text, jsonb)    to service_role;
grant execute on function public.mark_notification_read(uuid)           to authenticated, service_role;
grant execute on function public.mark_all_notifications_read()          to authenticated, service_role;
