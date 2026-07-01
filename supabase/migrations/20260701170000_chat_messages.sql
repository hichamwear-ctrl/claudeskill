-- ============================================================================
-- M6 — Chat d'EXÉCUTION (client ↔ intervenant, mission active)
-- Réf. CHAT.md, DATA_MODEL §7.1, BUSINESS_RULES (BR-CHAT-*), NOTIFICATIONS.
--
-- P9 (séparation STRICTE) : ce chat n'a AUCUN lien avec l'intake
-- (`conversations`/`conversation_turns`). Tables, RLS, règles et notifications
-- distinctes. Le chat n'existe qu'à partir de `assigned` et jusqu'à la clôture.
--
-- Choix LEAN : AUCUNE Edge Function. Envoi = INSERT gardé par la RLS + trigger de
-- modération déterministe (sans IA) ; lecture = PostgREST + Postgres Changes ;
-- frappe = Broadcast ; accusés de lecture = RPC. Toute la logique critique en base.
-- ============================================================================

-- Lecteur de texte depuis app_config (jsonb string), avec défaut.
create or replace function public.config_text(p_key text, p_default text)
returns text
language sql
stable
set search_path = ''
as $$
  select coalesce(
    (select value #>> '{}' from public.app_config where key = p_key and is_active),
    p_default
  );
$$;

-- Participant d'une mission (client, intervenant affecté, ou admin). SECURITY
-- DEFINER : lecture de `missions` indépendante de la RLS de l'appelant (réutilisé
-- par la RLS de `messages` ET l'autorisation Realtime).
create or replace function public.is_mission_participant(p_mission_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.missions m
    where m.id = p_mission_id
      and (
        m.client_id = (select auth.uid())
        or m.operator_id = (select auth.uid())
        or public.current_user_role() = 'admin'
      )
  );
$$;

-- ----------------------------------------------------------------------------
-- messages : fil d'exécution (append-only). Évolutivité intégrée dès V1 :
--   `media jsonb` (photos/documents/vocaux/pièces jointes), `kind` (system/call…),
--   `body` nullable (message média seul), `metadata` (modération, group_key).
-- ----------------------------------------------------------------------------
create table public.messages (
  id         uuid primary key default gen_random_uuid(),
  mission_id uuid not null references public.missions(id) on delete cascade,
  sender_id  uuid not null references public.profiles(id) on delete cascade,
  kind       text not null default 'user' check (kind in ('user', 'system')),
  body       text,
  media      jsonb,                                  -- [{type,path,mime,size}] — futur
  read_at    timestamptz,
  metadata   jsonb not null default '{}'::jsonb,     -- modération, group_key, chiffrement futur
  created_at timestamptz not null default now(),
  constraint messages_content_present check (coalesce(btrim(body), '') <> '' or media is not null)
);

-- Pagination par keyset + historique ; index partiel pour le calcul des non-lus.
create index messages_thread_idx on public.messages (mission_id, created_at desc, id);
create index messages_unread_idx on public.messages (mission_id) where read_at is null;

comment on table public.messages is
  'Chat d''exécution (append-only). Distinct de conversation_turns (intake, P9).';

-- ----------------------------------------------------------------------------
-- Modération DÉTERMINISTE (sans IA) : détecte coordonnées (email/tel/URL) et
-- applique la politique app_config.chat.moderation (mask|warn|block). Longueur
-- bornée par chat.max_len. Une IA pourra COMPLÉTER plus tard (non requise).
-- ----------------------------------------------------------------------------
create or replace function public.moderate_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  c_email constant text := '[[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}';
  c_url   constant text := '(https?://|www\.)[[:graph:]]+';
  c_phone constant text := '\+?[0-9][0-9 .()\-]{6,}[0-9]';
  v_policy text := public.config_text('chat.moderation', 'mask');
  v_maxlen int := public.config_int('chat.max_len', 2000);
  v_reasons text[] := '{}';
  v_body text := new.body;
  v_jwt_role text := coalesce(
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb) ->> 'role', '');
begin
  -- Anti-usurpation : seul le serveur (service_role) peut créer un message
  -- `system` (jalons cosmétiques). Tout envoi utilisateur est forcé en 'user'.
  new.kind := coalesce(new.kind, 'user');
  if v_jwt_role <> 'service_role' then
    new.kind := 'user';
  end if;

  if v_body is not null then
    if length(v_body) > v_maxlen then
      raise exception 'message trop long (max %)', v_maxlen using errcode = 'check_violation';
    end if;
    if v_body ~ c_email then v_reasons := array_append(v_reasons, 'email'); end if;
    if v_body ~ c_url   then v_reasons := array_append(v_reasons, 'url');   end if;
    if v_body ~ c_phone then v_reasons := array_append(v_reasons, 'phone'); end if;

    if array_length(v_reasons, 1) is not null then
      if v_policy = 'block' then
        raise exception 'contenu interdit (coordonnées personnelles)' using errcode = 'check_violation';
      elsif v_policy = 'mask' then
        v_body := regexp_replace(v_body, c_email, '[masqué]', 'g');
        v_body := regexp_replace(v_body, c_url,   '[masqué]', 'g');
        v_body := regexp_replace(v_body, c_phone, '[masqué]', 'g');
        new.body := v_body;
        new.metadata := new.metadata
          || jsonb_build_object('moderated', true, 'action', 'mask', 'reasons', to_jsonb(v_reasons));
      else -- 'warn' : on laisse passer mais on signale
        new.metadata := new.metadata
          || jsonb_build_object('flagged', true, 'action', 'warn', 'reasons', to_jsonb(v_reasons));
      end if;
    end if;
  end if;

  -- Clé de groupement pour la notification `chat_message` (NOTIFICATIONS.md).
  new.metadata := new.metadata || jsonb_build_object('group_key', new.mission_id::text);
  return new;
end;
$$;

create trigger messages_moderate
  before insert on public.messages
  for each row execute function public.moderate_message();

-- ----------------------------------------------------------------------------
-- Accusés de lecture : seul le DESTINATAIRE marque lus les messages reçus.
-- (messages append-only : aucune UPDATE directe ; read_at via cette RPC.)
-- ----------------------------------------------------------------------------
create or replace function public.mark_messages_read(p_mission_id uuid)
returns int
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid   uuid := (select auth.uid());
  v_count int;
begin
  if not public.is_mission_participant(p_mission_id) then
    raise exception 'accès refusé' using errcode = 'insufficient_privilege';
  end if;
  update public.messages set read_at = now()
  where mission_id = p_mission_id and sender_id <> v_uid and read_at is null;
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- ----------------------------------------------------------------------------
-- RLS : participants stricts. Lecture = participant/admin. Écriture = un des DEUX
-- participants, sender = soi, ET mission dans un état de chat OUVERT (assigned →
-- in_progress) — jamais avant l'affectation (P1) ni après clôture (lecture seule).
-- Aucune UPDATE/DELETE (append-only) : pas de grant → contournement impossible.
-- ----------------------------------------------------------------------------
alter table public.messages enable row level security;

create policy messages_read on public.messages
  for select to authenticated
  using (public.is_mission_participant(mission_id));

create policy messages_insert on public.messages
  for insert to authenticated
  with check (
    sender_id = (select auth.uid())
    and exists (
      select 1 from public.missions m
      where m.id = mission_id
        and (m.client_id = (select auth.uid()) or m.operator_id = (select auth.uid()))
        and m.status in ('assigned', 'shopping', 'preparing', 'en_route', 'arrived', 'in_progress')
    )
  );

grant select, insert on public.messages to authenticated;
grant execute on function public.config_text(text, text)          to authenticated, service_role;
grant execute on function public.is_mission_participant(uuid)      to authenticated, service_role;
grant execute on function public.mark_messages_read(uuid)          to authenticated, service_role;
