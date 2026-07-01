-- ============================================================================
-- M6 — Autorisation des canaux Realtime (correctif de sécurité Broadcast/Presence)
-- Réf. API_SPEC §7, GPS_TRACKING §9, CHAT.md §3, LEAN_V1 §0.
--
-- Les canaux Broadcast/Presence n'ont PAS de table sous-jacente → la RLS des
-- tables ne les protège pas. On sécurise l'ABONNEMENT lui-même via une policy sur
-- `realtime.messages` (Realtime Authorization) qui délègue la décision à une
-- fonction pure et TESTABLE `can_access_topic(topic)`. Défaut = DENY (fail-closed).
--
-- Couvre TOUS les canaux : chat, frappe, statut, ET position GPS (M7) — tout
-- `mission:{id}:*` exige d'être participant de la mission ; `conversation:{id}:*`
-- exige d'en être le propriétaire ; les canaux opérateur exigent le rôle.
-- ============================================================================

-- Propriétaire d'une conversation d'intake (ou admin). SECURITY DEFINER.
create or replace function public.owns_conversation(p_conversation_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.conversations c
    where c.id = p_conversation_id
      and (c.client_id = (select auth.uid()) or public.current_user_role() = 'admin')
  );
$$;

-- Décision d'accès à un canal Realtime, par convention de nommage du topic.
--   mission:{uuid}:*        -> participant de la mission (chat, typing, status, location GPS)
--   conversation:{uuid}:*   -> propriétaire de la conversation (intake) / admin
--   operator:review-inbox   -> rôle operator|admin
--   operator:presence       -> rôle operator|admin
--   (tout le reste)         -> DENY (fail-closed)
create or replace function public.can_access_topic(p_topic text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  if p_topic like 'mission:%' then
    v_id := split_part(p_topic, ':', 2)::uuid;      -- uuid invalide -> exception -> deny
    return public.is_mission_participant(v_id);
  elsif p_topic like 'conversation:%' then
    v_id := split_part(p_topic, ':', 2)::uuid;
    return public.owns_conversation(v_id);
  elsif p_topic in ('operator:review-inbox', 'operator:presence') then
    return public.current_user_role() in ('operator', 'admin');
  else
    return false;
  end if;
exception when others then
  return false;                                     -- topic malformé -> DENY
end;
$$;

comment on function public.can_access_topic is
  'Autorisation d''un canal Realtime par nommage du topic. Fail-closed. Testée directement.';

grant execute on function public.owns_conversation(uuid)  to authenticated, service_role;
grant execute on function public.can_access_topic(text)   to authenticated, service_role;

-- ----------------------------------------------------------------------------
-- Policies sur `realtime.messages` (présentes sur Supabase ; absentes en test
-- local). On les crée UNIQUEMENT si le schéma Realtime existe — la logique de
-- décision (`can_access_topic`) est, elle, testée directement.
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (
    select 1 from information_schema.tables
    where table_schema = 'realtime' and table_name = 'messages'
  ) then
    execute $p$
      create policy chat_realtime_read on realtime.messages
        for select to authenticated
        using (public.can_access_topic((select realtime.topic())))
    $p$;
    execute $p$
      create policy chat_realtime_write on realtime.messages
        for insert to authenticated
        with check (public.can_access_topic((select realtime.topic())))
    $p$;
  end if;
end;
$$;
