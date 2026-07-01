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
