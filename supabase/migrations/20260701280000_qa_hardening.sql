-- ============================================================================
-- M11 — Durcissement QA : « mission non démarrable » sans autorisation ACTIVE
-- Réf. BUSINESS_RULES BR-214, SPEC §5. Correction issue de la revue E2E.
--
-- Problème trouvé : la garde M9 ne bloquait le départ d'exécution que si une
-- autorisation était `expired` — pas si elle était ABSENTE. Un `accepted→assigned`
-- manuel (opérateur/admin, hors flux paiement) permettait donc de DÉMARRER une
-- mission sans que le client ait payé. On exige désormais une autorisation ACTIVE
-- (`requires_capture`) pour quitter `assigned` vers une étape d'exécution.
-- Couvre : absente, expirée, annulée, remboursée → toutes bloquent le démarrage.
-- ============================================================================

create or replace function public.guard_payment_authorization()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.status = 'assigned' and new.status in ('shopping', 'preparing', 'en_route')
     and not exists (
       select 1 from public.payments p
       where p.mission_id = new.id and p.status = 'requires_capture'
     ) then
    raise exception 'mission non démarrable : autorisation de paiement active requise (BR-214)'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;
