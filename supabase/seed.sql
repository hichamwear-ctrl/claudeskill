-- ============================================================================
-- Seed — données de démonstration (rejoué à chaque `supabase db reset`).
-- Ces données sont ADMINISTRABLES en production (panneau admin) ; elles ne sont
-- ici que pour disposer d'un environnement de démo complet et reproductible.
-- Inserts idempotents (on conflict) pour pouvoir rejouer sans erreur.
-- ============================================================================

-- --- Catalogue de services (SPEC_FONCTIONNELLE_V1 §1.1) ----------------------
-- Étapes d'exécution : désormais en données (category_workflow), plus en colonnes.
insert into public.service_categories
  (family, slug, label, icon, base_fee, prep_buffer_min, legal_note, metadata, sort_order)
values
  ('shopping',     'groceries',      'Courses alimentaires',        'cart',     4.90, 20, null,                                                                  '{}'::jsonb,                    10),
  ('shopping',     'pharmacy',       'Pharmacie (sans ordonnance)', 'pill',     5.90, 15, 'Produits sans ordonnance uniquement.',                                '{}'::jsonb,                    20),
  ('courier',      'parcel',         'Livraison de colis',          'package',  5.90,  5, null,                                                                  '{}'::jsonb,                    30),
  ('auto',         'car_assist',     'Dépannage auto simple',       'car',      9.90, 15, 'Interventions simples (batterie, pneu, carburant). Hors remorquage.', '{}'::jsonb,                    40),
  ('home_service', 'daily_help',     'Services du quotidien',       'home',     6.90, 10, null,                                                                  '{}'::jsonb,                    50),
  ('custom',       'custom_request', 'Demande libre',               'sparkles', 0.00,  0, 'Tarif fixé par devis.',                                               '{"quote_only": true}'::jsonb,  60)
on conflict (slug) do nothing;

-- Workflow d'exécution par catégorie (généralise requires_shopping/preparation).
-- Courses & pharmacie passent par l'étape `shopping` (avec preuve = ticket).
insert into public.category_workflow (category_id, status, sort_order, requires_proof)
select sc.id, 'shopping', 10, true
from public.service_categories sc
where sc.slug in ('groceries', 'pharmacy')
  and not exists (
    select 1 from public.category_workflow w where w.category_id = sc.id and w.status = 'shopping'
  );

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
  ('night_window',                    '{"from":"22:00","to":"06:00"}'::jsonb,'server','Plage nuit (supplément futur)'),
  ('classification.min_confidence',   '0.6'::jsonb,                         'server', 'Seuil de confiance de classification'),
  ('conversation.ttl_hours',          '24'::jsonb,                          'server', 'Expiration d''une conversation d''intake (h)'),
  ('conversation.max_questions',      '12'::jsonb,                          'server', 'Nb max de questions par dialogue'),
  ('feature.tips_enabled',            'true'::jsonb,                        'public', 'Pourboire (simulé) activé'),
  ('feature.gps_background',          'false'::jsonb,                       'public', 'Suivi GPS en arrière-plan'),
  ('chat.allow_media',                'true'::jsonb,                        'public', 'Autoriser les médias dans le chat'),
  ('chat.moderation',                 '"mask"'::jsonb,                      'server', 'Politique anti-coordonnées : mask|warn|block'),
  ('chat.retention_days',             '90'::jsonb,                          'server', 'Rétention des messages (jours)'),
  ('chat.max_len',                    '2000'::jsonb,                        'public', 'Longueur max d''un message'),
  ('chat.read_receipts',              'true'::jsonb,                        'public', 'Accusés de lecture activés'),
  ('gps.broadcast_interval_sec',      '2'::jsonb,                           'public', 'Fréquence d''émission live (s)'),
  ('gps.upsert_sec',                  '20'::jsonb,                          'public', 'Fréquence d''upsert dernière position (s)'),
  ('gps.min_distance_m',              '15'::jsonb,                          'public', 'Distance mini avant nouvel envoi (anti-bruit, batterie)'),
  ('gps.desired_accuracy',            '"balanced"'::jsonb,                  'public', 'Précision demandée : balanced|high'),
  ('gps.active_states',               '["en_route","arrived"]'::jsonb,      'public', 'États où la carte client est active'),
  ('gps.nearby_radius_m',             '500'::jsonb,                         'public', 'Seuil « intervenant proche » (m)'),
  ('gps.arrival_radius_m',            '80'::jsonb,                          'public', 'Seuil de détection d''arrivée (m)'),
  ('gps.stale_after_sec',             '30'::jsonb,                          'public', 'Position considérée périmée (repli UI, s)'),
  ('gps.retention_days',              '30'::jsonb,                          'server', 'Rétention (purge) de la dernière position (j)'),
  ('notifications.quiet_hours',       '{"from":"22:00","to":"07:00"}'::jsonb,'server','Silence nocturne (heure locale)'),
  ('notifications.min_interval_sec',  '60'::jsonb,                          'server', 'Intervalle mini entre 2 push d''un même type (anti-spam)'),
  ('notifications.retention_days',    '90'::jsonb,                          'server', 'Rétention des notifications (purge)'),
  ('notifications.token_stale_days',  '60'::jsonb,                          'server', 'Jeton d''appareil périmé après N jours sans activité'),
  ('classification.keywords',
   '{"groceries":["course","courses","supermarché","supermarche","lait","pain","aliment","épicerie","epicerie"],"pharmacy":["pharmacie","médicament","medicament","paracétamol","doliprane","sans ordonnance"],"parcel":["colis","paquet","livrer","livraison","déposer","deposer"],"car_assist":["voiture","pneu","batterie","carburant","panne","dépannage","depannage"],"daily_help":["aide","ménage","menage","bricolage","jardin","quotidien"]}'::jsonb,
   'server', 'Mots-clés de classification par catégorie (moteur V1, éditable — P0)')
on conflict (key) do nothing;

-- --- Contenus / i18n (échantillon) — content_strings ----------------------------
insert into public.content_strings (key, locale, value, description) values
  ('home.prompt',            'fr', 'De quoi avez-vous besoin aujourd''hui ?', 'Accueil (P0)'),
  ('home.prompt',            'en', 'What do you need today?',                 'Accueil (P0)'),
  ('notif.request_accepted.title', 'fr', 'Demande acceptée',                  'Notification'),
  ('notif.request_accepted.body',  'fr', 'Votre demande a été acceptée. Vous pouvez procéder au paiement.', 'Notification'),
  ('err.payment_locked',     'fr', 'Le paiement sera possible après validation de votre demande.', 'Erreur UX')
on conflict (key, locale) do nothing;

-- --- Textes des questions (labels) — content_strings ----------------------------
insert into public.content_strings (key, locale, value) values
  ('q.generic.details.label', 'fr', 'Pouvez-vous préciser votre besoin ?'),
  ('q.generic.address.label', 'fr', 'À quelle adresse ?'),
  ('q.generic.when.label',    'fr', 'Pour quand ?'),
  ('q.generic.photo.label',   'fr', 'Une photo peut-elle aider ? (facultatif)'),
  ('q.groceries.store.label', 'fr', 'Quelle enseigne ?'),
  ('q.groceries.items.label', 'fr', 'Que faut-il acheter ?'),
  ('q.groceries.budget.label','fr', 'Budget estimé des achats (€) ?'),
  ('opt.store.carrefour',     'fr', 'Carrefour'),
  ('opt.store.delhaize',      'fr', 'Delhaize'),
  ('opt.store.colruyt',       'fr', 'Colruyt'),
  ('opt.store.other',         'fr', 'Autre / peu importe')
on conflict (key, locale) do nothing;

-- --- Set GÉNÉRIQUE universel (category_id NULL) — P11 ----------------------------
insert into public.question_sets (slug, name, category_id, sort_order)
values ('generic', 'Demande générique', null, 0)
on conflict (slug) do nothing;

insert into public.questions (set_id, key, type, label_key, sort_order, required_when)
select s.id, q.key, q.type::public.question_type, q.label_key, q.ord, q.req::jsonb
from public.question_sets s
cross join (values
  ('details', 'text',    'q.generic.details.label', 10, '{"always":true}'),
  ('address', 'address', 'q.generic.address.label', 20, '{"always":true}'),
  ('when',    'text',    'q.generic.when.label',    30, '{}'),
  ('photo',   'photo',   'q.generic.photo.label',   40, '{}')
) as q(key, type, label_key, ord, req)
where s.slug = 'generic'
  and not exists (select 1 from public.questions x where x.set_id = s.id and x.key = q.key);

-- --- Set spécifique 'groceries' (raffinement) -----------------------------------
insert into public.question_sets (slug, name, category_id, sort_order)
select 'groceries', 'Courses alimentaires', sc.id, 10
from public.service_categories sc where sc.slug = 'groceries'
on conflict (slug) do nothing;

insert into public.questions (set_id, key, type, label_key, sort_order, required_when, validation)
select s.id, q.key, q.type::public.question_type, q.label_key, q.ord, q.req::jsonb, q.val::jsonb
from public.question_sets s
cross join (values
  ('store',  'select', 'q.groceries.store.label',  10, '{}',             '{}'),
  ('items',  'text',   'q.groceries.items.label',  20, '{"always":true}','{"maxLen":500}'),
  ('budget', 'number', 'q.groceries.budget.label', 30, '{}',             '{"min":0}')
) as q(key, type, label_key, ord, req, val)
where s.slug = 'groceries'
  and not exists (select 1 from public.questions x where x.set_id = s.id and x.key = q.key);

-- Options de la question 'store' (select)
insert into public.question_options (question_id, value, label_key, sort_order)
select qq.id, o.value, o.label_key, o.ord
from public.questions qq
join public.question_sets s on s.id = qq.set_id and s.slug = 'groceries'
cross join (values
  ('carrefour', 'opt.store.carrefour', 10),
  ('delhaize',  'opt.store.delhaize',  20),
  ('colruyt',   'opt.store.colruyt',   30),
  ('other',     'opt.store.other',     40)
) as o(value, label_key, ord)
where qq.key = 'store'
  and not exists (select 1 from public.question_options x where x.question_id = qq.id and x.value = o.value);

-- --- Notifications (M8) : catalogue data-driven ---------------------------------
-- Textes (content_strings) — AUCUN texte en dur ailleurs. (request_accepted déjà seedé.)
insert into public.content_strings (key, locale, value) values
  ('notif.request_rejected.title',      'fr', 'Demande refusée'),
  ('notif.request_rejected.body',       'fr', 'Votre demande n''a pas pu être acceptée. {reason}'),
  ('notif.request_needs_info.title',    'fr', 'Informations demandées'),
  ('notif.request_needs_info.body',     'fr', 'Nous avons besoin de précisions pour votre demande.'),
  ('notif.mission_completed.title',     'fr', 'Mission terminée'),
  ('notif.mission_completed.body',      'fr', 'Votre mission est terminée. Votre reçu est disponible.'),
  ('notif.mission_cancelled.title',     'fr', 'Mission annulée'),
  ('notif.mission_cancelled.body',      'fr', 'Votre mission a été annulée.'),
  ('notif.refund_simulated.title',      'fr', 'Remboursement'),
  ('notif.refund_simulated.body',       'fr', 'Un remboursement a été effectué pour votre mission.'),
  ('notif.chat_message.title',          'fr', 'Nouveau message'),
  ('notif.chat_message.body',           'fr', 'Vous avez reçu un nouveau message.'),
  ('notif.new_request_to_review.title', 'fr', 'Nouvelle demande'),
  ('notif.new_request_to_review.body',  'fr', 'Une nouvelle demande attend votre revue.'),
  ('notif.mission_new.title',           'fr', 'Nouvelle mission'),
  ('notif.mission_new.body',            'fr', 'Une mission vous a été affectée.')
on conflict (key, locale) do nothing;

-- Templates (par type & audience) — que des clés, aucun texte.
insert into public.notification_templates
  (key, audience, channel, title_key, body_key, deep_link_template, metadata)
values
  ('request_accepted',      'client',   'both', 'notif.request_accepted.title',      'notif.request_accepted.body',      'app://payment/{mission_id}',           '{"bypass_quiet_hours":true}'::jsonb),
  ('request_rejected',      'client',   'both', 'notif.request_rejected.title',      'notif.request_rejected.body',      'app://mission/{mission_id}',           '{}'::jsonb),
  ('request_needs_info',    'client',   'both', 'notif.request_needs_info.title',    'notif.request_needs_info.body',    'app://conversation/{conversation_id}', '{"bypass_quiet_hours":true}'::jsonb),
  ('mission_completed',     'client',   'both', 'notif.mission_completed.title',     'notif.mission_completed.body',     'app://mission/{mission_id}',           '{"bypass_quiet_hours":true}'::jsonb),
  ('mission_cancelled',     'client',   'both', 'notif.mission_cancelled.title',     'notif.mission_cancelled.body',     'app://mission/{mission_id}',           '{"bypass_quiet_hours":true}'::jsonb),
  ('refund_simulated',      'client',   'both', 'notif.refund_simulated.title',      'notif.refund_simulated.body',      'app://payment/{mission_id}',           '{}'::jsonb),
  ('chat_message',          'client',   'push', 'notif.chat_message.title',          'notif.chat_message.body',          'app://chat/{mission_id}',              '{"bypass_quiet_hours":true,"group_key":"{mission_id}"}'::jsonb),
  ('chat_message',          'operator', 'push', 'notif.chat_message.title',          'notif.chat_message.body',          'app://chat/{mission_id}',              '{"bypass_quiet_hours":true}'::jsonb),
  ('new_request_to_review', 'operator', 'both', 'notif.new_request_to_review.title', 'notif.new_request_to_review.body', 'app://review/{mission_id}',            '{}'::jsonb),
  ('mission_new',           'operator', 'push', 'notif.mission_new.title',           'notif.mission_new.body',           'app://mission/{mission_id}',           '{}'::jsonb)
on conflict (key, audience) do nothing;

-- Déclencheurs (événement → template). Ajouter une notif = insérer une ligne.
insert into public.notification_triggers (event_key, template_key, audience) values
  ('mission.status.accepted',          'request_accepted',      'client'),
  ('mission.status.rejected',          'request_rejected',      'client'),
  ('mission.status.needs_information', 'request_needs_info',    'client'),
  ('mission.status.completed',         'mission_completed',     'client'),
  ('mission.status.cancelled',         'mission_cancelled',     'client'),
  ('mission.event.refund',             'refund_simulated',      'client'),
  ('chat.message',                     'chat_message',          'client'),
  ('chat.message',                     'chat_message',          'operator'),
  ('mission.status.pending_review',    'new_request_to_review', 'operator'),
  ('mission.status.assigned',          'mission_new',           'operator')
on conflict (event_key, template_key, audience) do nothing;
