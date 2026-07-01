-- ============================================================================
-- M5 — Paiement simulé (Stripe-ready) : ledger `payments`
-- Réf. DATA_MODEL §5.2, BUSINESS_RULES §5 (BR-210→216), SPEC §5, LEAN_V1 §1.1.
--
-- UNE seule table : `payments` = miroir fidèle du cycle d'un PaymentIntent
-- (autorisation → capture → remboursement). Les avances/pourboires vivent en
-- colonnes sur `missions` (absorption LEAN_V1) ; `payment_methods` différée (mock).
--
-- Invariants CRITIQUES (P1) tenus côté BASE (RPC M5, migration suivante), jamais
-- seulement dans l'Edge : aucune autorisation hors `accepted`, capture ≤ autorisé,
-- 1 paiement par mission. Le domaine ne connaît AUCUN PSP (référence opaque).
-- ============================================================================

-- Statuts miroir du cycle Stripe (simulés fidèlement par le MockPaymentProvider).
create type public.payment_status as enum (
  'pending',            -- intent créé, réponse PSP non encore enregistrée
  'requires_capture',   -- autorisé (fonds réservés)
  'succeeded',          -- capturé en totalité
  'partially_captured', -- capturé partiellement (reste libéré)
  'canceled',           -- autorisation annulée (void, avant capture)
  'refunded',           -- remboursé (après capture)
  'failed'              -- échec PSP
);

create table public.payments (
  id                    uuid primary key default gen_random_uuid(),
  mission_id            uuid not null unique references public.missions(id) on delete cascade,
  client_id             uuid not null references public.profiles(id) on delete restrict,
  provider              text not null default 'mock' check (provider in ('mock', 'stripe')),
  provider_pi_ref       text,                                   -- réf opaque (sim_pi_… / pi_…)
  provider_customer_ref text,
  amount_authorized     numeric(10, 2),
  amount_captured       numeric(10, 2),
  amount_refunded       numeric(10, 2),
  currency              text not null default 'eur',
  status                public.payment_status not null default 'pending',
  authorized_at         timestamptz,
  captured_at           timestamptz,
  metadata              jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);
create index payments_client_idx on public.payments (client_id, created_at desc);

comment on table public.payments is
  'Ledger paiement (1/mission), miroir du cycle PSP. Écrit uniquement par les RPC M5.';

create trigger payments_set_updated_at
  before update on public.payments
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- RLS : le client lit SON paiement ; admin total. AUCUNE écriture directe :
-- tout passe par les RPC SECURITY DEFINER (garde-fous P1 non contournables).
-- ----------------------------------------------------------------------------
alter table public.payments enable row level security;

create policy payments_read on public.payments
  for select to authenticated
  using (client_id = (select auth.uid()) or public.current_user_role() = 'admin');

grant select on public.payments to authenticated;
