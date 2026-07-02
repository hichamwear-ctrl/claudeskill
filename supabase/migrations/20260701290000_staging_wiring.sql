-- ============================================================================
-- M12 — Câblage staging : Realtime (Postgres Changes), Storage proofs, push réel
-- Réf. Architecture §10/§14, NOTIFICATIONS.md, GPS_TRACKING/CHAT (canaux).
--
-- AUCUNE fonctionnalité métier. Uniquement le câblage d'infrastructure qui ne
-- pouvait être posé avant l'existence des tables métier / hors stack Supabase.
-- Tout est GARDÉ (conditionnel) : neutre en local, actif en staging Supabase.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) Livraison push : trace de livraison + trigger de déclenchement (async).
--    L'ÉCRITURE des notifications reste faite en SQL (M9) ; ici on ne fait que
--    DÉCLENCHER l'envoi push (transport) via send-push, sans logique métier.
-- ----------------------------------------------------------------------------
alter table public.notifications add column if not exists delivered_at timestamptz;

create or replace function public.deliver_notification_push()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_url    text;
  v_secret text;
begin
  if not new.pushed then return null; end if;   -- seulement les notifs à pousser
  -- Désactivé par défaut (local) ; activé en staging via app_config.
  if coalesce((select value #>> '{}' from public.app_config where key = 'notifications.push_enabled'), 'false') <> 'true' then
    return null;
  end if;
  v_url := coalesce((select value #>> '{}' from public.app_config where key = 'notifications.send_push_url'), '');
  if v_url = '' then return null; end if;
  v_secret := coalesce((select value #>> '{}' from public.app_config where key = 'notifications.webhook_secret'), '');

  -- pg_net (async, ne bloque pas). Référence DYNAMIQUE : l'extension n'est pas
  -- requise à la création (neutre en local). Un échec de push ne casse JAMAIS la
  -- transaction métier.
  begin
    execute format(
      'select net.http_post(url := %L, headers := %L::jsonb, body := %L::jsonb)',
      v_url,
      jsonb_build_object('Content-Type', 'application/json', 'x-webhook-secret', v_secret)::text,
      jsonb_build_object('notification_id', new.id::text)::text
    );
  exception when others then
    null;
  end;
  return null;
end;
$$;

create trigger notifications_deliver_push
  after insert on public.notifications
  for each row execute function public.deliver_notification_push();

comment on function public.deliver_notification_push is
  'Déclenche l''envoi push (send-push) via pg_net. Gardé par app_config ; neutre si désactivé.';

-- ----------------------------------------------------------------------------
-- 2) Realtime — Postgres Changes : exposer les tables persistées aux canaux
--    (mission:{id}:chat = messages ; mission:{id}:status = missions ; timeline).
--    La RLS des tables s'applique EN PLUS (chaque abonné ne reçoit que ses lignes).
--    Idempotent + gardé (la publication n'existe qu'en environnement Supabase).
-- ----------------------------------------------------------------------------
do $$
declare t text;
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    foreach t in array array['messages', 'missions', 'mission_events', 'notifications'] loop
      if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t
      ) then
        execute format('alter publication supabase_realtime add table public.%I', t);
      end if;
    end loop;
  end if;
end;
$$;

-- ----------------------------------------------------------------------------
-- 3) Storage — bucket `mission-proofs` : accès aux PARTICIPANTS de la mission.
--    (La policy était différée en attendant la table missions — désormais posée.)
--    Convention de chemin : mission-proofs/{mission_id}/<fichier>.
--    Gardé (le schéma storage n'existe qu'en environnement Supabase).
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (select 1 from information_schema.tables
             where table_schema = 'storage' and table_name = 'objects') then
    execute $p$
      create policy "mission_proofs_participant_read" on storage.objects
        for select to authenticated
        using (
          bucket_id = 'mission-proofs'
          and public.is_mission_participant(nullif((storage.foldername(name))[1], '')::uuid)
        )
    $p$;
    execute $p$
      create policy "mission_proofs_participant_write" on storage.objects
        for insert to authenticated
        with check (
          bucket_id = 'mission-proofs'
          and public.is_mission_participant(nullif((storage.foldername(name))[1], '')::uuid)
        )
    $p$;
  end if;
end;
$$;
