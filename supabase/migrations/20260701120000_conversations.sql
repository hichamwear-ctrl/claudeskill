-- ============================================================================
-- M2.2 — Conversations d'intake (moteur conversationnel)
-- Réf. CONVERSATION_ENGINE, DATA_MODEL §4.5, LEAN_V1 §1.1
--
-- Système d'INTAKE (comprendre le besoin -> pending_review). Totalement séparé
-- du chat d'exécution `messages` (P9). Données OPÉRATIONNELLES (non versionnées).
-- Écriture serveur uniquement (converse en service_role) ; le client lit.
-- ============================================================================

-- Statut d'une conversation d'intake.
create type public.conversation_status as enum ('active', 'submitted', 'abandoned', 'expired');

-- ----------------------------------------------------------------------------
-- conversations : session de dialogue ; state = mémoire de travail UNIQUE
--   { answers: {key:val}, active_sets: [slug], position, classification, plan }
-- ----------------------------------------------------------------------------
create table public.conversations (
  id         uuid primary key default gen_random_uuid(),
  client_id  uuid not null references public.profiles(id) on delete cascade,
  status     public.conversation_status not null default 'active',
  locale     text not null default 'fr',
  state      jsonb not null default '{}'::jsonb,   -- mémoire de travail (slots, position, plan...)
  metadata   jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz                            -- TTL (app_config.conversation.ttl_hours), posé par le serveur
);
create index conversations_client_idx  on public.conversations (client_id, created_at desc);
create index conversations_active_idx  on public.conversations (status)     where status = 'active';
create index conversations_expires_idx on public.conversations (expires_at) where status = 'active';

comment on table public.conversations is
  'Conversation d''intake (constitution du besoin). state = mémoire de travail unique.';

create trigger conversations_set_updated_at
  before update on public.conversations
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- conversation_turns : historique IMMUABLE des tours (append-only).
--   role = user | assistant | system (convention ; check, extensible).
-- ----------------------------------------------------------------------------
create table public.conversation_turns (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role            text not null check (role in ('user', 'assistant', 'system')),
  content         text,                              -- nullable : un tour peut être média seul
  media           jsonb,
  slot_key        text,                              -- question.key visée/renseignée
  extracted       jsonb,                             -- valeurs extraites par l'IA (propositions)
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now()
);
create index conversation_turns_conv_idx on public.conversation_turns (conversation_id, created_at);

comment on table public.conversation_turns is
  'Tours de dialogue (append-only). Distinct de messages (chat d''exécution) — P9.';

-- ----------------------------------------------------------------------------
-- RLS : le client LIT sa conversation et ses tours ; ÉCRITURE serveur uniquement
-- (converse en service_role, qui contourne la RLS). Admin lit tout.
-- Aucun grant d'écriture à authenticated (défense en profondeur).
-- ----------------------------------------------------------------------------
alter table public.conversations      enable row level security;
alter table public.conversation_turns enable row level security;

create policy conversations_read_self on public.conversations
  for select to authenticated
  using (client_id = (select auth.uid()) or public.current_user_role() = 'admin');

create policy conversation_turns_read_self on public.conversation_turns
  for select to authenticated
  using (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_turns.conversation_id
        and (c.client_id = (select auth.uid()) or public.current_user_role() = 'admin')
    )
  );

-- Lecture seule pour l'app ; l'écriture passe par les Edge Functions (service_role).
grant select on public.conversations      to authenticated;
grant select on public.conversation_turns to authenticated;
