-- ============================================================================
-- M7 — Durcissement de l'autorisation Realtime en ÉCRITURE (publication)
-- Réf. API_SPEC §7, GPS_TRACKING §9. Audit de sécurité (renforcement).
--
-- Faiblesse identifiée en M6 : `can_access_topic` gardait lecture ET écriture de
-- façon identique → un CLIENT (participant) pouvait PUBLIER de fausses positions
-- sur `mission:{id}:location` ou usurper `:status`. On sépare donc :
--   • can_access_topic  (SELECT/abonnement) : tout participant/propriétaire ;
--   • can_publish_topic (INSERT/broadcast)  : plus strict, selon le canal.
--
--   mission:{id}:location -> SEUL l'intervenant affecté (ou admin) publie ;
--   mission:{id}:typing   -> les deux participants ;
--   mission:{id}:chat     -> participants (le chat passe par la table, mais on
--                            verrouille aussi le canal) ;
--   mission:{id}:status   -> PERSONNE (serveur seul, via Postgres Changes) ;
--   conversation:{id}:*   -> propriétaire ;
--   operator:presence     -> rôle operator/admin (sa propre présence) ;
--   operator:review-inbox -> PERSONNE (serveur seul) ;
--   (reste)               -> DENY.
-- ============================================================================

-- L'appelant est-il l'intervenant AFFECTÉ à la mission (ou admin) ?
create or replace function public.is_mission_operator(p_mission_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.missions m
    where m.id = p_mission_id
      and (m.operator_id = (select auth.uid()) or public.current_user_role() = 'admin')
  );
$$;

-- Décision d'ÉCRITURE (broadcast/presence) sur un canal. Fail-closed.
create or replace function public.can_publish_topic(p_topic text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_id     uuid;
  v_suffix text;
begin
  if p_topic like 'mission:%' then
    v_id := split_part(p_topic, ':', 2)::uuid;       -- uuid invalide -> exception -> deny
    v_suffix := split_part(p_topic, ':', 3);
    if v_suffix = 'location' then
      return public.is_mission_operator(v_id);        -- SEUL l'intervenant émet sa position
    elsif v_suffix in ('typing', 'chat') then
      return public.is_mission_participant(v_id);
    else
      return false;                                   -- status & autres : serveur seul
    end if;
  elsif p_topic like 'conversation:%' then
    v_id := split_part(p_topic, ':', 2)::uuid;
    return public.owns_conversation(v_id);
  elsif p_topic = 'operator:presence' then
    return public.current_user_role() in ('operator', 'admin');
  else
    return false;                                     -- review-inbox & inconnus : DENY
  end if;
exception when others then
  return false;
end;
$$;

comment on function public.can_publish_topic is
  'Autorisation d''ÉCRITURE Realtime (broadcast/presence). Plus stricte que la lecture. Fail-closed.';

grant execute on function public.is_mission_operator(uuid) to authenticated, service_role;
grant execute on function public.can_publish_topic(text)   to authenticated, service_role;

-- ----------------------------------------------------------------------------
-- Remplace la policy d'écriture `realtime.messages` (M6) pour utiliser la
-- décision durcie. Conditionnel : uniquement si le schéma Realtime est présent.
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (
    select 1 from information_schema.tables
    where table_schema = 'realtime' and table_name = 'messages'
  ) then
    execute 'drop policy if exists chat_realtime_write on realtime.messages';
    execute $p$
      create policy chat_realtime_write on realtime.messages
        for insert to authenticated
        with check (public.can_publish_topic((select realtime.topic())))
    $p$;
  end if;
end;
$$;
