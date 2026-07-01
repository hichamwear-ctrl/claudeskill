-- ============================================================================
-- M8 — Notifications (100 % piloté par la donnée, indépendant du transport)
-- Réf. NOTIFICATIONS.md, DATA_MODEL §2.3/§3.12/§7.2, API_SPEC §4.9, SPEC §6.
--
-- Pipeline (exact) :
--   événement → notification_triggers → notification_templates → content_strings
--             → dispatch_notifications (RPC) → notifications  → send-push (transport)
--
-- Aucun texte en dur : les templates ne portent que des CLÉS (content_strings).
-- Idempotence ROBUSTE : contrainte UNIQUE `notifications.dedup_key`.
-- 4 tables uniquement (notification_preferences reste différée — LEAN_V1).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- device_tokens : jetons push par appareil (multi-appareils), propriétaire only.
--   `token` volontairement générique (Expo/FCM/APNS/web) — transport-agnostique.
-- ----------------------------------------------------------------------------
create table public.device_tokens (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.profiles(id) on delete cascade,
  platform   text not null check (platform in ('ios', 'android', 'web')),
  token      text not null,
  active     boolean not null default true,
  last_seen  timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (user_id, token)
);
create index device_tokens_user_idx on public.device_tokens (user_id) where active;

-- ----------------------------------------------------------------------------
-- notification_templates : gabarit par (type, audience). AUCUN texte, que des clés.
-- ----------------------------------------------------------------------------
create table public.notification_templates (
  key                text not null,
  audience           text not null check (audience in ('client', 'operator', 'admin')),
  channel            text not null check (channel in ('push', 'inapp', 'both')),
  title_key          text not null,               -- -> content_strings
  body_key           text,                          -- -> content_strings (optionnel)
  deep_link_template text,                          -- ex. app://mission/{mission_id}
  is_active          boolean not null default true,
  metadata           jsonb not null default '{}'::jsonb,  -- bypass_quiet_hours, group_key, priority
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  primary key (key, audience)
);
create trigger notification_templates_set_updated_at
  before update on public.notification_templates
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- notification_triggers : mapping événement → template(s). Many-to-many éditable.
-- ----------------------------------------------------------------------------
create table public.notification_triggers (
  id           uuid primary key default gen_random_uuid(),
  event_key    text not null,                       -- ex. mission.status.accepted, chat.message
  template_key text not null,                        -- réf. LÂCHE (absence gérée gracieusement)
  audience     text not null check (audience in ('client', 'operator', 'admin')),
  condition    jsonb,                                -- {} = toujours ; {"context_eq":{...}}
  is_active    boolean not null default true,
  sort_order   int not null default 0,
  unique (event_key, template_key, audience)
);
create index notification_triggers_event_idx on public.notification_triggers (event_key) where is_active;

comment on table public.notification_triggers is
  'Mapping événement→template (data-driven). Ajouter une notif = insérer une ligne.';

-- ----------------------------------------------------------------------------
-- notifications : historique/ledger (in-app + trace de push). Écrit par la RPC.
--   `dedup_key` UNIQUE = idempotence (même événement → jamais 2 notifications).
-- ----------------------------------------------------------------------------
create table public.notifications (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.profiles(id) on delete cascade,
  template   text not null,                          -- = notification_templates.key
  channel    text not null,
  title      text not null,
  body       text,
  deep_link  text,
  payload    jsonb not null default '{}'::jsonb,
  mission_id uuid references public.missions(id) on delete set null,
  dedup_key  text not null unique,                   -- idempotence robuste
  pushed     boolean not null default false,
  read_at    timestamptz,
  created_at timestamptz not null default now()
);
create index notifications_user_idx   on public.notifications (user_id, created_at desc);
create index notifications_unread_idx on public.notifications (user_id) where read_at is null;

comment on table public.notifications is
  'Historique des notifications (in-app + trace push). Écrit par dispatch_notifications.';

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------
alter table public.device_tokens          enable row level security;
alter table public.notification_templates enable row level security;
alter table public.notification_triggers  enable row level security;
alter table public.notifications          enable row level security;

-- device_tokens : propriétaire uniquement (l'app enregistre/retire ses jetons).
create policy device_tokens_owner on public.device_tokens
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- templates & triggers : configuration — lecture/écriture admin (serveur = service_role).
create policy notification_templates_admin on public.notification_templates
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');
create policy notification_triggers_admin on public.notification_triggers
  for all to authenticated
  using (public.current_user_role() = 'admin')
  with check (public.current_user_role() = 'admin');

-- notifications : destinataire (+ admin) en lecture ; écriture serveur only.
create policy notifications_read on public.notifications
  for select to authenticated
  using (user_id = (select auth.uid()) or public.current_user_role() = 'admin');

grant select, insert, update, delete on public.device_tokens          to authenticated;
grant select, insert, update, delete on public.notification_templates to authenticated;
grant select, insert, update, delete on public.notification_triggers  to authenticated;
grant select on public.notifications to authenticated;
