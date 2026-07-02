-- ============================================================================
-- M9 — Automatisation : événements → notifications (câblage)
-- Réf. NOTIFICATIONS.md §2, Architecture §14, API_SPEC §4.9.
--
-- CHOIX (challengé) : au lieu de Database Webhooks (pg_net → send-push) pour
-- l'ÉCRITURE des notifications, des TRIGGERS SQL appellent `dispatch_notifications`
-- directement. Avantages : transactionnel, IDEMPOTENT (dedup_key), sans pg_net,
-- sans nouvelle Edge, et TESTABLE en base. Le push réel (transport Expo) reste
-- `send-push`, câblable en production via Database Webhook sur `notifications`.
--
-- `conversations` n'émet AUCUNE notification en V1 : les notifs d'intake passent
-- par `mission_events` (pending_review → new_request_to_review). Pas de trigger.
-- ============================================================================

-- Chaque transition de mission -> notification(s) résolue(s) en base.
create or replace function public.on_mission_event_notify()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_conv uuid;
begin
  select conversation_id into v_conv from public.missions where id = new.mission_id;
  perform public.dispatch_notifications(
    'mission.status.' || new.to_status,
    jsonb_strip_nulls(jsonb_build_object(
      'mission_id', new.mission_id::text,
      'conversation_id', v_conv::text,
      'source_ref', new.id::text,
      'reason', new.metadata ->> 'reason'
    ))
  );
  return null;   -- AFTER trigger
end;
$$;

create trigger mission_events_notify
  after insert on public.mission_events
  for each row execute function public.on_mission_event_notify();

-- Chaque message d'exécution (utilisateur) -> notification `chat.message`.
create or replace function public.on_message_notify()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.kind = 'user' then
    perform public.dispatch_notifications(
      'chat.message',
      jsonb_build_object(
        'mission_id', new.mission_id::text,
        'sender_id', new.sender_id::text,
        'source_ref', new.id::text
      )
    );
  end if;
  return null;
end;
$$;

create trigger messages_notify
  after insert on public.messages
  for each row execute function public.on_message_notify();

-- Remboursement -> notification `mission.event.refund` (les autres transitions
-- paiement passent par mission_events : assign -> mission_new, etc.).
create or replace function public.on_payment_notify()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status = 'refunded' and old.status is distinct from 'refunded' then
    perform public.dispatch_notifications(
      'mission.event.refund',
      jsonb_build_object('mission_id', new.mission_id::text, 'source_ref', new.id::text || ':refund')
    );
  end if;
  return null;
end;
$$;

create trigger payments_notify
  after update on public.payments
  for each row execute function public.on_payment_notify();
