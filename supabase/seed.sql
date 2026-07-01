-- ============================================================================
-- Seed — données de démonstration (rejoué à chaque `supabase db reset`).
-- Ces données sont ADMINISTRABLES en production (panneau admin) ; elles ne sont
-- ici que pour disposer d'un environnement de démo complet et reproductible.
-- Inserts idempotents (on conflict) pour pouvoir rejouer sans erreur.
-- ============================================================================

-- --- Catalogue de services (SPEC_FONCTIONNELLE_V1 §1.1) ----------------------
insert into public.service_categories
  (family, slug, label, icon, base_fee, prep_buffer_min,
   requires_shopping, requires_preparation, legal_note, sort_order)
values
  ('shopping',     'groceries',      'Courses alimentaires',        'cart',     4.90, 20, true,  false, null,                                                              10),
  ('shopping',     'pharmacy',       'Pharmacie (sans ordonnance)', 'pill',     5.90, 15, true,  false, 'Produits sans ordonnance uniquement.',                            20),
  ('courier',      'parcel',         'Livraison de colis',          'package',  5.90,  5, false, false, null,                                                              30),
  ('auto',         'car_assist',     'Dépannage auto simple',       'car',      9.90, 15, false, false, 'Interventions simples (batterie, pneu, carburant). Hors remorquage.', 40),
  ('home_service', 'daily_help',     'Services du quotidien',       'home',     6.90, 10, false, false, null,                                                              50),
  ('custom',       'custom_request', 'Demande libre',               'sparkles', 0.00,  0, false, false, 'Tarif fixé par devis.',                                           60)
on conflict (slug) do nothing;

-- --- Zone de démonstration : Bruxelles (rectangle approximatif) --------------
-- Une seule ville pour la V1 ; ajouter une ville = insérer une ligne (aucun code).
insert into public.coverage_zones (slug, name, area)
values (
  'brussels', 'Bruxelles',
  ST_MakeEnvelope(4.28, 50.78, 4.48, 50.91, 4326)::geography  -- bbox approx.
)
on conflict (slug) do nothing;

-- Horaires : 7j/7, 08:00–22:00 (idempotent : seedé seulement si la zone n'en a pas).
insert into public.service_windows (zone_id, weekday, opens_at, closes_at)
select z.id, wd, time '08:00', time '22:00'
from public.coverage_zones z
cross join generate_series(0, 6) as wd
where z.slug = 'brussels'
  and not exists (select 1 from public.service_windows sw where sw.zone_id = z.id);
