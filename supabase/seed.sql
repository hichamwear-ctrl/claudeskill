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

-- --- Tarif par défaut (global) — SPEC §3.1 --------------------------------------
insert into public.pricing_rules
  (code, zone_id, base_fare, price_per_km, minimum_price, authorization_margin_pct, avg_speed_kmh, currency)
values
  ('default', null, 3.50, 0.90, 5.00, 20, 25, 'eur')
on conflict (code) do nothing;

-- --- Paramètres app_config (seuils, délais, flags) — BUSINESS_RULES §0.3 etc. ---
-- Curated V1 ; les clés des fonctionnalités différées seront ajoutées avec elles.
insert into public.app_config (key, value, scope, description) values
  ('review.claim_ttl_min',            '15'::jsonb,                          'server', 'Expiration d''un claim de revue (min)'),
  ('quote_validity_hours',            '24'::jsonb,                          'server', 'Validité d''un prix proposé (h)'),
  ('price_tolerance_pct',             '20'::jsonb,                          'server', 'Écart de prix toléré sans réaccord'),
  ('cancellation_free_window_min',    '5'::jsonb,                           'server', 'Annulation client sans frais (min)'),
  ('delay_grace_min',                 '10'::jsonb,                          'server', 'Tolérance avant « en retard » (min)'),
  ('unreachable_timeout_min',         '10'::jsonb,                          'server', 'Délai avant « client injoignable » (min)'),
  ('payment_authorization_ttl_min',   '60'::jsonb,                          'server', 'Durée de vie d''une autorisation sim (min)'),
  ('dispute_window_hours',            '72'::jsonb,                          'server', 'Fenêtre d''ouverture de litige (h)'),
  ('max_concurrent_missions',         '1'::jsonb,                           'server', 'Charge max par intervenant (V1=1)'),
  ('nearby_radius_m',                 '500'::jsonb,                         'server', 'Seuil « intervenant proche » (m)'),
  ('night_window',                    '{"from":"22:00","to":"06:00"}'::jsonb,'server','Plage nuit (supplément futur)'),
  ('classification.min_confidence',   '0.6'::jsonb,                         'server', 'Seuil de confiance de classification'),
  ('conversation.ttl_hours',          '24'::jsonb,                          'server', 'Expiration d''une conversation d''intake (h)'),
  ('conversation.max_questions',      '12'::jsonb,                          'server', 'Nb max de questions par dialogue'),
  ('feature.tips_enabled',            'true'::jsonb,                        'public', 'Pourboire (simulé) activé'),
  ('feature.gps_background',          'false'::jsonb,                       'public', 'Suivi GPS en arrière-plan')
on conflict (key) do nothing;

-- --- Contenus / i18n (échantillon) — content_strings ----------------------------
insert into public.content_strings (key, locale, value, description) values
  ('home.prompt',            'fr', 'De quoi avez-vous besoin aujourd''hui ?', 'Accueil (P0)'),
  ('home.prompt',            'en', 'What do you need today?',                 'Accueil (P0)'),
  ('notif.request_accepted.title', 'fr', 'Demande acceptée',                  'Notification'),
  ('notif.request_accepted.body',  'fr', 'Votre demande a été acceptée. Vous pouvez procéder au paiement.', 'Notification'),
  ('err.payment_locked',     'fr', 'Le paiement sera possible après validation de votre demande.', 'Erreur UX')
on conflict (key, locale) do nothing;
