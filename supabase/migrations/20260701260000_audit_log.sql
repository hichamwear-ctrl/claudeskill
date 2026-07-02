-- ============================================================================
-- M10 — Traçabilité : audit_log générique (append-only) + audit auto de la config
-- Réf. DATA_MODEL §8.2, ADMIN_PANEL §1/§AD-25, BUSINESS_RULES BR-224, LEAN_V1 §1.1.
--
-- UNE table générique journalise TOUT changement de configuration (catalogue,
-- questions, tarifs, workflows, zones, textes, notifications, app_config). Écrite
-- UNIQUEMENT par trigger SECURITY DEFINER ; lecture admin ; aucune suppression.
--
-- Audit (revue) : les tables de config ont déjà une RLS d'écriture ADMIN ; on ne
-- crée donc PAS de RPC d'édition par table (sur-ingénierie) — les écritures
-- directes (admin) sont journalisées ici, et validées par validate_config (M10).
-- ============================================================================

create table public.audit_log (
  id          uuid primary key default gen_random_uuid(),
  actor_id    uuid references public.profiles(id) on delete set null,
  actor_role  public.user_role,
  table_name  text not null,
  record_key  text,                                  -- clé naturelle (slug/key/code/id)
  action      text not null check (action in ('insert', 'update', 'delete')),
  old_value   jsonb,
  new_value   jsonb,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index audit_log_table_idx on public.audit_log (table_name, created_at desc);
create index audit_log_actor_idx on public.audit_log (actor_id, created_at desc);

comment on table public.audit_log is
  'Journal générique append-only des changements de configuration. Écrit par trigger.';

-- ----------------------------------------------------------------------------
-- Trigger générique : capture insert/update/delete de config → audit_log.
--   record_key = 1re clé naturelle disponible (slug/key/code/id).
-- ----------------------------------------------------------------------------
create or replace function public.audit_config_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_key text;
begin
  if tg_op = 'DELETE' then
    v_old := to_jsonb(old); v_new := null;
  elsif tg_op = 'INSERT' then
    v_old := null; v_new := to_jsonb(new);
  else
    v_old := to_jsonb(old); v_new := to_jsonb(new);
  end if;

  v_key := coalesce(
    v_new ->> 'slug', v_new ->> 'key', v_new ->> 'code', v_new ->> 'id',
    v_old ->> 'slug', v_old ->> 'key', v_old ->> 'code', v_old ->> 'id'
  );

  insert into public.audit_log (actor_id, actor_role, table_name, record_key, action, old_value, new_value)
  values (
    (select auth.uid()), public.current_user_role(), tg_table_name, v_key, lower(tg_op), v_old, v_new
  );
  return coalesce(new, old);
end;
$$;

-- Attache l'audit à TOUTES les tables de configuration (data-driven).
do $$
declare t text;
begin
  foreach t in array array[
    'service_categories', 'question_sets', 'questions', 'question_options',
    'pricing_rules', 'category_workflow', 'coverage_zones', 'service_windows',
    'content_strings', 'notification_templates', 'notification_triggers', 'app_config'
  ] loop
    execute format(
      'create trigger %I_audit after insert or update or delete on public.%I
         for each row execute function public.audit_config_change()', t, t);
  end loop;
end;
$$;

-- ----------------------------------------------------------------------------
-- Garde d'intégrité SÛRE (n'empêche pas le brouillonnage) : une option ne peut
-- exister que sur une question de type select/multiselect (anti-« option orpheline »).
-- ----------------------------------------------------------------------------
create or replace function public.guard_question_option()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1 from public.questions q
    where q.id = new.question_id and q.type in ('select', 'multiselect')
  ) then
    raise exception 'option invalide : la question cible n''est pas select/multiselect'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create trigger question_options_guard
  before insert or update on public.question_options
  for each row execute function public.guard_question_option();

-- ----------------------------------------------------------------------------
-- RLS : lecture admin uniquement ; append-only (aucun grant d'écriture ; le
-- trigger SECURITY DEFINER écrit). Aucune UPDATE/DELETE possible.
-- ----------------------------------------------------------------------------
alter table public.audit_log enable row level security;

create policy audit_log_admin_read on public.audit_log
  for select to authenticated
  using (public.current_user_role() = 'admin');

grant select on public.audit_log to authenticated;
