-- ============================================================================
-- M9 — Tâches planifiées (expirations + purges RGPD) & garde d'autorisation
-- Réf. BUSINESS_RULES (BR-CE-71, BR-214), CHAT §6, GPS_TRACKING §9, NOTIFICATIONS §11.
--
-- Toute la logique = RPC SQL idempotentes & re-lançables (aucune Edge, aucun TS).
-- pg_cron ne fait qu'APPELER ces RPC (planification, conditionnelle à l'extension).
-- Seuils/rétentions = `app_config` (aucune valeur en dur).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Garde « mission non démarrable » si l'autorisation de paiement a expiré
-- (BR-214). Trigger BEFORE UPDATE additif : ne touche pas transition_mission.
--   « démarrer » = quitter `assigned` vers une étape d'exécution.
-- ----------------------------------------------------------------------------
create or replace function public.guard_payment_authorization()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.status = 'assigned' and new.status in ('shopping', 'preparing', 'en_route')
     and exists (
       select 1 from public.payments p
       where p.mission_id = new.id and p.status = 'expired'
     ) then
    raise exception 'autorisation de paiement expirée (mission non démarrable)'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create trigger missions_guard_authorization
  before update of status on public.missions
  for each row execute function public.guard_payment_authorization();

-- ----------------------------------------------------------------------------
-- Expiration des conversations d'intake inactives (BR-CE-71).
--   `active` + inactif > conversation.ttl_hours → `expired`. Historique conservé
--   (aucune suppression de tours). L'immuabilité est déjà garantie par les gardes
--   existantes (converse/create_mission refusent hors `active`).
-- ----------------------------------------------------------------------------
create or replace function public.expire_conversations()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  update public.conversations set status = 'expired'
  where status = 'active'
    and updated_at < now() - make_interval(hours => public.config_int('conversation.ttl_hours', 24));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- ----------------------------------------------------------------------------
-- Expiration des autorisations de paiement non capturées (BR-214).
--   `requires_capture` + autorisé depuis > payment_authorization_ttl_min → `expired`.
--   Effet : plus capturable (payment_intent exige requires_capture) + mission non
--   démarrable (garde ci-dessus).
-- ----------------------------------------------------------------------------
create or replace function public.expire_payment_authorizations()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  update public.payments set status = 'expired'
  where status = 'requires_capture'
    and authorized_at is not null
    and authorized_at < now() - make_interval(mins => public.config_int('payment_authorization_ttl_min', 60));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- ----------------------------------------------------------------------------
-- Purges RGPD (rétentions en app_config). Suppressions ESPACÉES, jamais brutales.
-- ----------------------------------------------------------------------------
create or replace function public.purge_notifications()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  delete from public.notifications
  where created_at < now() - make_interval(days => public.config_int('notifications.retention_days', 90));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.purge_operator_locations()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  delete from public.operator_locations
  where updated_at < now() - make_interval(days => public.config_int('gps.retention_days', 30));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.purge_messages()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  delete from public.messages
  where created_at < now() - make_interval(days => public.config_int('chat.retention_days', 90));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.cleanup_device_tokens()
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare v_count int;
begin
  delete from public.device_tokens
  where active = false
     or last_seen < now() - make_interval(days => public.config_int('notifications.token_stale_days', 60));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

grant execute on function public.expire_conversations()            to service_role;
grant execute on function public.expire_payment_authorizations()   to service_role;
grant execute on function public.purge_notifications()             to service_role;
grant execute on function public.purge_operator_locations()        to service_role;
grant execute on function public.purge_messages()                  to service_role;
grant execute on function public.cleanup_device_tokens()           to service_role;

-- ----------------------------------------------------------------------------
-- Planification pg_cron (uniquement si l'extension est présente — Supabase).
-- En local (extension absente), on saute : les RPC restent testées directement.
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('expire-conversations',      '*/15 * * * *', 'select public.expire_conversations();');
    perform cron.schedule('expire-payment-auth',       '*/5 * * * *',  'select public.expire_payment_authorizations();');
    perform cron.schedule('purge-notifications',       '30 3 * * *',   'select public.purge_notifications();');
    perform cron.schedule('purge-operator-locations',  '20 3 * * *',   'select public.purge_operator_locations();');
    perform cron.schedule('purge-messages',            '10 3 * * *',   'select public.purge_messages();');
    perform cron.schedule('cleanup-device-tokens',     '0 3 * * *',    'select public.cleanup_device_tokens();');
  end if;
end;
$$;
