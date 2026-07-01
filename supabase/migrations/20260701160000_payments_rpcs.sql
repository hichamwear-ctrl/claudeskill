-- ============================================================================
-- M5 — Fonctions serveur du paiement (garde-fous métier NON contournables)
-- Réf. API_SPEC §4.6/§4.7/§4.8/§4.10, BUSINESS_RULES §5, SPEC §5.
--
-- Modèle « intent → PSP → settle » (fidèle aux PaymentIntents Stripe) :
--   • payment_intent  : GARDE (accepté/propriété/prix/état) + prépare l'action ;
--   • [Edge]          : appelle PaymentProvider (mock aujourd'hui) ;
--   • payment_settle  : enregistre le résultat PSP + transition mission couplée.
-- Le domaine (SQL) ignore tout PSP : `provider_pi_ref` est une référence OPAQUE.
-- Toute la logique critique (P1 : jamais d'autorisation hors `accepted`, capture
-- ≤ autorisé) vit ICI, pas dans l'Edge (simple adaptateur).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- assign_mission : affectation auto après autorisation (accepted → assigned).
--   Serveur uniquement (appelée par payment_settle). L'intervenant V1 = celui
--   qui a accepté (reviewed_by), mono-opérateur.
-- ----------------------------------------------------------------------------
create or replace function public.assign_mission(p_mission_id uuid, p_actor uuid default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_from public.mission_status;
  v_rev  uuid;
begin
  select status, reviewed_by into v_from, v_rev
  from public.missions where id = p_mission_id for update;
  if not found then
    raise exception 'mission introuvable' using errcode = 'no_data_found';
  end if;
  if v_from <> 'accepted' then
    raise exception 'affectation impossible depuis %', v_from using errcode = 'check_violation';
  end if;

  update public.missions
  set status = 'assigned', operator_id = coalesce(operator_id, v_rev)
  where id = p_mission_id;

  insert into public.mission_events (mission_id, from_status, to_status, actor_id, actor_role, metadata)
  values (p_mission_id, 'accepted', 'assigned', p_actor, null, jsonb_build_object('via', 'authorization'));
end;
$$;

-- ----------------------------------------------------------------------------
-- payment_intent : garde-fou + préparation d'une action de paiement.
--   Retourne { payment_id, amount, currency, provider }. Appelée AVEC le JWT de
--   l'appelant : le gate P1 (propriété client, rôle) est vérifié via auth.uid().
-- ----------------------------------------------------------------------------
create or replace function public.payment_intent(p_mission_id uuid, p_action text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_role     public.user_role := public.current_user_role();
  v_uid      uuid := (select auth.uid());
  m          public.missions%rowtype;
  v_pay      public.payments%rowtype;
  v_base     numeric;
  v_margin   numeric;
  v_currency text;
  v_amount   numeric;
  v_pid      uuid;
begin
  select * into m from public.missions where id = p_mission_id for update;
  if not found then
    raise exception 'mission introuvable' using errcode = 'no_data_found';
  end if;
  select * into v_pay from public.payments where mission_id = p_mission_id;

  if p_action = 'authorize' then
    -- P1 : autorisation UNIQUEMENT si acceptée ET par le client propriétaire.
    if m.status <> 'accepted' then
      raise exception 'payment_locked' using errcode = 'check_violation';
    end if;
    if v_role <> 'admin' and m.client_id is distinct from v_uid then
      raise exception 'appelant non propriétaire' using errcode = 'insufficient_privilege';
    end if;
    if m.quoted_price is not null and m.quote_expires_at is not null
       and m.quote_expires_at < now() then
      raise exception 'price_expired' using errcode = 'check_violation';
    end if;
    if v_pay.id is not null then
      raise exception 'paiement déjà initié' using errcode = 'unique_violation';
    end if;

    v_base := coalesce(m.quoted_price, m.estimated_price);
    if v_base is null then
      raise exception 'prix non défini (validation opérateur requise)' using errcode = 'not_null_violation';
    end if;
    select coalesce(authorization_margin_pct, 0), currency into v_margin, v_currency
    from public.pricing_rules where is_active and zone_id is null limit 1;
    v_margin := coalesce(v_margin, 0);
    v_currency := coalesce(v_currency, 'eur');
    -- BR-211 : autorisé = prix × (1 + marge%) + avance estimée.
    v_amount := round(v_base * (1 + v_margin / 100.0) + coalesce(m.advance_estimate, 0), 2);

    insert into public.payments (mission_id, client_id, amount_authorized, currency, status)
    values (p_mission_id, m.client_id, v_amount, v_currency, 'pending')
    returning id into v_pid;
    return jsonb_build_object('payment_id', v_pid, 'amount', v_amount, 'currency', v_currency, 'provider', 'mock');
  end if;

  -- Actions post-autorisation : un paiement doit exister.
  if v_pay.id is null then
    raise exception 'aucun paiement' using errcode = 'no_data_found';
  end if;

  if p_action = 'capture' then
    if v_role <> 'admin' and m.operator_id is distinct from v_uid then
      raise exception 'intervenant non affecté' using errcode = 'insufficient_privilege';
    end if;
    if m.status <> 'in_progress' then
      raise exception 'capture hors clôture' using errcode = 'check_violation';
    end if;
    if v_pay.status <> 'requires_capture' then
      raise exception 'paiement non capturable' using errcode = 'check_violation';
    end if;
    return jsonb_build_object('payment_id', v_pay.id, 'amount', v_pay.amount_authorized,
      'currency', v_pay.currency, 'provider', v_pay.provider);
  end if;

  if p_action = 'void' then
    if v_role not in ('operator', 'admin') then
      raise exception 'rôle non autorisé' using errcode = 'insufficient_privilege';
    end if;
    if v_pay.status <> 'requires_capture' then
      raise exception 'void impossible (non autorisé)' using errcode = 'check_violation';
    end if;
    return jsonb_build_object('payment_id', v_pay.id, 'amount', v_pay.amount_authorized,
      'currency', v_pay.currency, 'provider', v_pay.provider);
  end if;

  if p_action = 'refund' then
    if v_role not in ('operator', 'admin') then
      raise exception 'rôle non autorisé' using errcode = 'insufficient_privilege';
    end if;
    if v_pay.status not in ('succeeded', 'partially_captured') then
      raise exception 'refund impossible (non capturé)' using errcode = 'check_violation';
    end if;
    return jsonb_build_object('payment_id', v_pay.id, 'amount', v_pay.amount_captured,
      'currency', v_pay.currency, 'provider', v_pay.provider);
  end if;

  raise exception 'action inconnue: %', p_action using errcode = 'check_violation';
end;
$$;

-- ----------------------------------------------------------------------------
-- payment_settle : enregistre le résultat PSP + transition mission couplée.
--   Serveur uniquement (service_role). Re-vérifie les invariants (capture ≤
--   autorisé, preuve) même si l'Edge s'est trompé (défense en profondeur).
--   p_data : { amount, advance_actual?, proof_path? } selon l'action.
-- ----------------------------------------------------------------------------
create or replace function public.payment_settle(
  p_payment_id  uuid,
  p_action      text,
  p_provider    text,
  p_provider_ref text,
  p_ok          boolean,
  p_actor       uuid,
  p_data        jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_pay      public.payments%rowtype;
  v_amount   numeric := (p_data ->> 'amount')::numeric;
  v_advance  numeric := (p_data ->> 'advance_actual')::numeric;
  v_proof    text := p_data ->> 'proof_path';
  v_status   public.payment_status;
  v_final    numeric;
  m_status   public.mission_status;
begin
  select * into v_pay from public.payments where id = p_payment_id for update;
  if not found then
    raise exception 'paiement introuvable' using errcode = 'no_data_found';
  end if;

  -- Échec PSP : on marque failed (sauf pour void/refund où l'échec est ignoré V1).
  if not p_ok then
    update public.payments set status = 'failed', provider = p_provider, provider_pi_ref = p_provider_ref
    where id = p_payment_id;
    return jsonb_build_object('payment_id', p_payment_id, 'status', 'failed');
  end if;

  if p_action = 'authorize' then
    if v_pay.status <> 'pending' then
      raise exception 'autorisation déjà réglée' using errcode = 'check_violation';
    end if;
    update public.payments set
      status = 'requires_capture', provider = p_provider, provider_pi_ref = p_provider_ref,
      authorized_at = now()
    where id = p_payment_id;
    perform public.assign_mission(v_pay.mission_id, p_actor);   -- accepted → assigned (atomique)
    return jsonb_build_object('payment_id', p_payment_id, 'status', 'requires_capture',
      'amount_authorized', v_pay.amount_authorized);
  end if;

  if p_action = 'capture' then
    if v_pay.status <> 'requires_capture' then
      raise exception 'capture déjà réglée' using errcode = 'check_violation';
    end if;
    -- BR-212 : capture ≤ autorisé (revérifié en base).
    if v_amount is null or v_amount > v_pay.amount_authorized then
      raise exception 'montant capturé supérieur à l''autorisation' using errcode = 'check_violation';
    end if;
    -- BR-190 : preuve requise à la clôture.
    if coalesce(btrim(v_proof), '') = '' then
      raise exception 'preuve requise' using errcode = 'not_null_violation';
    end if;
    -- Verrou mission : capture uniquement en clôture.
    select status into m_status from public.missions where id = v_pay.mission_id for update;
    if m_status <> 'in_progress' then
      raise exception 'mission hors clôture' using errcode = 'check_violation';
    end if;

    v_status := case when v_amount >= v_pay.amount_authorized then 'succeeded' else 'partially_captured' end;
    v_final := v_amount + coalesce(v_advance, 0);
    update public.payments set
      status = v_status, amount_captured = v_amount, captured_at = now(),
      provider_pi_ref = coalesce(p_provider_ref, provider_pi_ref),
      metadata = metadata || jsonb_strip_nulls(jsonb_build_object('proof_path', v_proof))
    where id = p_payment_id;

    update public.missions set
      status = 'completed', completed_at = now(),
      final_amount = v_final, advance_actual = v_advance
    where id = v_pay.mission_id;
    insert into public.mission_events (mission_id, from_status, to_status, actor_id, actor_role, metadata)
    values (v_pay.mission_id, 'in_progress', 'completed', p_actor, 'operator',
      jsonb_build_object('via', 'capture', 'proof_path', v_proof));

    return jsonb_build_object('payment_id', p_payment_id, 'status', v_status, 'final_amount', v_final);
  end if;

  if p_action = 'void' then
    update public.payments set status = 'canceled', provider_pi_ref = coalesce(p_provider_ref, provider_pi_ref)
    where id = p_payment_id;
    return jsonb_build_object('payment_id', p_payment_id, 'status', 'canceled');
  end if;

  if p_action = 'refund' then
    update public.payments set
      status = 'refunded', amount_refunded = coalesce(v_amount, amount_captured),
      provider_pi_ref = coalesce(p_provider_ref, provider_pi_ref)
    where id = p_payment_id;
    return jsonb_build_object('payment_id', p_payment_id, 'status', 'refunded');
  end if;

  raise exception 'action inconnue: %', p_action using errcode = 'check_violation';
end;
$$;

-- ----------------------------------------------------------------------------
-- Privilèges : intent avec le JWT appelant (gate P1) ; settle & assign serveur.
-- ----------------------------------------------------------------------------
grant execute on function public.payment_intent(uuid, text)                             to authenticated, service_role;
grant execute on function public.payment_settle(uuid, text, text, text, boolean, uuid, jsonb) to service_role;
grant execute on function public.assign_mission(uuid, uuid)                             to service_role;
