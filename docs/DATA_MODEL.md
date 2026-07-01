# DATA MODEL — Modèle de données fonctionnel — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Objectif :** un modèle **piloté par la donnée**, conçu pour évoluer plusieurs
> années **sans modifier le code** à chaque nouveau besoin. Le code est un
> **moteur générique** qui interprète des tables de configuration, de règles et
> de contenu.
>
> **Cohérence :** aligné avec `PRD.md`, `BUSINESS_RULES.md`,
> `SPEC_FONCTIONNELLE_V1.md`, `UX_SPEC.md`, `Architecture_Technique.md`.
> Ce document consolide et **fait référence** pour le schéma ; le DDL exact vit
> dans les migrations. Colonnes chiffrées/paramètres : **en base**, jamais en dur.

---

## 1. Principes de conception

### 1.1 Trois couches

1. **Structure (stable)** — entités cœur : `profiles`, `missions`, `payments`,
   `messages`… Leur forme change rarement.
2. **Configuration & règles (data-driven)** — catalogue, workflow, tarifs, zones,
   horaires, **questions dynamiques**, **transitions**, **modèles de
   notifications**, seuils, flags. Administrable, **sans redéploiement**.
3. **Contenu & i18n (éditable)** — tous les textes affichés (`content_strings`).

### 1.2 Règles d'or

- **Rien codé en dur** de ce qui peut changer (texte, seuil, règle, étape).
- **`metadata jsonb`** sur chaque entité mutable → attributs futurs sans migration.
- **Conditions** exprimées dans un **mini‑langage JSON borné** (§12), jamais du code
  arbitraire.
- **Effets** sensibles (paiement, transitions) restent **en code** typé/testé ;
  seule leur **éligibilité** est en donnée.
- **Sécurité** (contrôle humain, RLS) : jamais uniquement configurable.
- Conventions : PK `uuid` (`gen_random_uuid()`), `created_at`/`updated_at`
  `timestamptz`, RLS **activée partout**, index sur FK + colonnes de filtre.

### 1.3 Légende de statut (par table)

`✅ livré` (migrations M1.1/M1.2) · `🧩 socle` (identité/auth déjà livrés) ·
`🔜 à construire` · `🅥2 V2`.

---

## 2. Couche Identité & comptes

### 2.1 `profiles` 🧩
- **Rôle :** profil applicatif lié 1‑1 à `auth.users`.
- **Colonnes clés :** `id` (PK=auth.users), `role user_role`, `first_name?`,
  `last_name?`, `email?`, `phone?`, `avatar_url?`, `locale`, `metadata jsonb`
  *(à ajouter)*, `created_at`, `updated_at`.
- **Relations :** 1‑1 `auth.users` ; 1‑1 `operator_profiles` ; 1‑N `addresses`,
  `device_tokens`, `missions` (client), `messages`, `notifications`.
- **Index :** PK ; (rôle si besoin de listing admin).
- **Contraintes :** FK `on delete cascade` ; `locale not null default 'fr'`.
- **RLS :** lecture/écriture de son profil ; admin total ; anti‑escalade de rôle
  (trigger). *(déjà en place)*
- **Edge Functions :** `custom_access_token_hook` (lecture rôle).
- **Écrans :** C‑05, C‑29, OP‑14, AD‑08.
- **Règles :** contrôle humain (rôle décideur `operator`/`admin`).

### 2.2 `operator_profiles` 🔜
- **Rôle :** données spécifiques intervenant.
- **Colonnes :** `id` (PK=profiles.id), `status operator_status`, `vehicle_type?`,
  `vehicle_plate?`, `rating_avg`, `rating_count`, `stripe_account?` (🅥2),
  `is_verified`, `documents jsonb`, `metadata jsonb`, timestamps.
- **Relations :** 1‑1 `profiles` ; 1‑N `missions` (operator), `advances`,
  `payouts`, `ratings` ; 1‑1 `operator_locations`.
- **Index :** PK ; `status` (dispatch) ; GIST via `operator_locations`.
- **Contraintes :** `rating_avg` 0–5.
- **RLS :** l'intervenant lit/écrit le sien ; le client lit le profil **public**
  de l'intervenant de SA mission ; admin total.
- **Edge Functions :** `assign-mission` (dispatch, lecture dispo).
- **Écrans :** OP‑02, OP‑03, OP‑05 (dashboard), AD‑08.
- **Règles :** BR‑040→045 (disponibilité), vérification `is_verified` `[ADMIN]`.
- **💡 Généricité :** `documents jsonb` évite une table `operator_documents`
  tant que le volume/queries restent simples.

### 2.3 `device_tokens` 🔜
- **Rôle :** jetons push par appareil (multi‑appareils).
- **Colonnes :** `id`, `user_id`, `expo_token`, `platform`, `last_seen`.
- **Relations :** N‑1 `profiles`.
- **Index :** `unique (user_id, expo_token)`.
- **RLS :** propriétaire uniquement.
- **Edge Functions :** `send-push` (lecture).
- **Écrans :** C‑06 (permissions), toutes (réception).
- **Règles :** `NOTIFICATIONS.md`.

### 2.4 `addresses` 🔜
- **Rôle :** adresses du client (domicile, bureau…).
- **Colonnes :** `id`, `user_id`, `label?`, `formatted`, `details?`,
  `location geography(point,4326)`, `is_default`, `metadata jsonb`, timestamps.
- **Relations :** N‑1 `profiles` ; référencée par `missions.dropoff_address`.
- **Index :** `addresses_user_idx`, GIST `location`.
- **Contraintes :** un seul `is_default` par user (trigger/partial unique).
- **RLS :** propriétaire uniquement ; admin lecture.
- **Edge Functions :** `zone-check` (via point), `estimate-price`.
- **Écrans :** C‑11, C‑12.
- **Règles :** BR‑080→082 (adresse incomplète/impossible).

---

## 3. Couche Référentiel & configuration (pilotée par la donnée)

> **Principe fondateur — moteur de demandes (à garder en tête pour toute cette
> couche) :** l'utilisateur **ne choisit jamais** de catégorie. Il décrit
> librement son besoin (« De quoi avez‑vous besoin aujourd'hui ? »). Le système
> (IA + règles, §3.14) **classe** la demande vers une `service_categories`
> (taxonomie **interne**), puis charge le `question_set` correspondant. Ajouter un
> métier (serrurier, plombier, montage IKEA, jardinage, garde d'animaux…) =
> **enrichir les données** (catégorie + questions + indices de classification +
> workflow + tarifs), **jamais** le code.

### 3.1 `service_categories` ✅ (à faire évoluer)
- **Rôle :** **taxonomie interne** des services (cible de classification), **non**
  un menu présenté au client. Administrable et **ouverte** : tout nouveau métier
  s'ajoute par insertion.
- **Colonnes :** `id`, `family mission_family`, `slug`, `label`, `icon?`,
  `is_active`, `fulfillment`, `legal_note?`, `base_fee`, `prep_buffer_min`,
  `sort_order`, `metadata jsonb`, timestamps.
- **⚠️ Évolution :** les booléens `requires_shopping`/`requires_preparation`
  (livrés en M1.1) sont **remplacés** par `category_workflow` (§3.2). À la reprise
  du dev, une migration les retire (aucune dépendance encore).
- **Relations :** 1‑N `missions`, `category_workflow`, `question_sets`.
- **Index :** `family (where is_active)`, `sort_order`, `unique(slug)`.
- **Contraintes :** `fulfillment in ('self','partner')`, `base_fee >= 0`.
- **RLS :** lecture authentifiée (actives ; admin voit tout) ; écriture admin.
- **Edge Functions :** `estimate-price` (lecture `base_fee`/`prep_buffer_min`).
- **Écrans :** C‑07, C‑09, AD‑05.
- **Règles :** §1 SPEC ; BR‑010, BR‑050→053, BR‑182 (`metadata.requires_proof`).

### 3.2 `category_workflow` 🔜 *(nouveau — généralise les étapes)*
- **Rôle :** étapes **optionnelles** d'exécution activées par catégorie, ordonnées.
  Généralise `requires_shopping`/`requires_preparation` → ajouter une étape future
  (ex. `quality_check`) = insérer une ligne, **aucune colonne ni code**.
- **Colonnes :** `id`, `category_id`, `status mission_status`, `sort_order`,
  `requires_proof boolean`, `is_active`.
- **Relations :** N‑1 `service_categories`.
- **Index :** `unique(category_id, status)`, `(category_id, sort_order)`.
- **Contraintes :** `status` ∈ étapes optionnelles autorisées (ex. `shopping`,
  `preparing`, extensible).
- **RLS :** lecture authentifiée ; écriture admin.
- **Edge Functions :** `transition_mission` (étapes offertes), UI cockpit.
- **Écrans :** OP‑06 (bouton d'étape), AD‑05.
- **Règles :** SPEC §2.5 (saut d'étapes piloté par la donnée).

### 3.3 `coverage_zones` ✅
- **Rôle :** zones couvertes (PostGIS). Une ville = une ligne.
- **Colonnes :** `id`, `slug?`, `name`, `area geography(polygon,4326)`,
  `is_active`, `metadata jsonb`, timestamps.
- **Relations :** 1‑N `service_windows`, `pricing_rules` (par zone).
- **Index :** GIST `area`, `unique(slug)`.
- **RLS :** lecture authentifiée (actives) ; écriture admin.
- **Edge Functions :** `zone-check` (`ST_Covers`).
- **Écrans :** C‑08, AD‑07.
- **Règles :** BR‑011, BR‑022 ; PRD‑F03.

### 3.4 `service_windows` ✅
- **Rôle :** créneaux d'ouverture par zone/jour.
- **Colonnes :** `id`, `zone_id`, `weekday 0..6`, `opens_at`, `closes_at`,
  `is_active`, `created_at`.
- **Relations :** N‑1 `coverage_zones`.
- **Index :** `(zone_id, weekday) where is_active`.
- **Contraintes :** `weekday 0..6`, `opens_at < closes_at` (nuit = 2 lignes).
- **RLS :** lecture authentifiée ; écriture admin.
- **Edge Functions :** `zone-check` (horaires).
- **Écrans :** C‑08, AD‑07. **Règles :** BR‑012, BR‑042.

### 3.5 `waitlist` ✅
- **Rôle :** demande latente hors zone.
- **Colonnes :** `id`, `user_id?`, `email?`, `phone?`, `location geography(point)`,
  `note?`, `created_at`.
- **RLS :** self‑insert ; lecture admin.
- **Écrans :** C‑08, AD‑12. **Règles :** PRD‑F03.

### 3.6 `app_config` 🔜 *(clé/valeur générique)*
- **Rôle :** **tous** les seuils, délais, limites, constantes métier — 1 endroit.
- **Colonnes :** `key text pk`, `value jsonb`, `description?`, `is_active`,
  `updated_by?`, `updated_at`.
- **RLS :** lecture authentifiée (clés publiques) ; écriture admin. *(Option :
  colonne `scope` public/serveur pour restreindre certaines clés au serveur.)*
- **Edge Functions :** toutes (lecture des seuils).
- **Écrans :** AD‑11.
- **Règles :** §0.3 BUSINESS_RULES (seuils) ; `CONVERSATION_ENGINE.md` §17
  (clés `classification.*`, `conversation.*`) ; flags `feature.*`.
- **💡 Généricité :** remplace **toute** constante métier, seuil et flag → évite
  N colonnes/tables.

### 3.7 Feature flags → **dans `app_config`** (décision produit)
- **Pas de table dédiée.** L'activation/désactivation d'une fonctionnalité est
  une **clé `app_config`** (`value jsonb` : booléen, nombre, chaîne ou objet de
  ciblage). **Une seule source de configuration** pour tous les paramètres et
  flags → maintenance simplifiée.
- Convention : clés `feature.<nom>` (ex. `feature.tips_enabled = true`,
  `feature.google_login = {"enabled":false}`).
- **Règle :** le code lit `app_config` ; jamais de flag codé en dur.

### 3.8 `pricing_rules` 🔜
- **Rôle :** paramètres tarifaires par zone (`zone_id NULL` = défaut).
- **Colonnes :** `id`, `zone_id?`, `base_fare`, `price_per_km`, `minimum_price`,
  `authorization_margin_pct`, `avg_speed_kmh`, `currency`, `is_active`, timestamps.
- **Relations :** N‑1 `coverage_zones`.
- **Index :** `(zone_id) where is_active`.
- **RLS :** lecture authentifiée ; écriture admin.
- **Edge Functions :** `estimate-price`.
- **Écrans :** AD‑06. **Règles :** SPEC §3.1 ; BR‑070, BR‑073, BR‑211.

### 3.9 `pricing_modifiers` 🔜 *(suppléments extensibles)*
- **Rôle :** suppléments (nuit/week‑end/férié/météo/urgence…) par insertion.
- **Colonnes :** `id`, `zone_id?`, `type`, `effect ('multiplier'|'fixed')`,
  `value`, `condition jsonb` (§12), `priority`, `is_active`, `valid_from?`,
  `valid_until?`.
- **RLS :** lecture authentifiée ; écriture admin.
- **Edge Functions :** `estimate-price` (application ordonnée).
- **Écrans :** AD‑06. **Règles :** SPEC §3.3.
- **💡 Généricité :** un seul modèle couvre **tous** les suppléments futurs →
  évite une colonne/table par type de supplément.

### 3.10 `content_strings` 🔜 *(i18n & copie éditable)*
- **Rôle :** **tous** les textes affichés (labels, erreurs, mentions, copie de
  notifications) éditables par locale.
- **Colonnes :** `key text`, `locale text`, `value text`, `description?`,
  `is_active`, `updated_at` — **PK `(key, locale)`**.
- **RLS :** lecture authentifiée ; écriture admin.
- **Edge Functions :** `send-push` (rendu templates), API (messages d'erreur).
- **Écrans :** tous (rendu) ; AD‑10/AD‑05 (édition).
- **💡 Généricité :** centralise la copie → aucun redéploiement pour un texte ;
  `service_categories.label`/`legal_note` peuvent **référencer** une `key`
  (ou rester en clair et être surchargés par `content_strings`).

### 3.11 Moteur de questions dynamiques 🔜
> Le client remplit un **formulaire généré depuis la base**. Le schéma est
> relationnel ; les **réponses** sont un JSONB sur la demande (`missions.details`).

#### `question_sets`
- **Rôle :** ensemble de questions rattaché à une catégorie (ou global).
- **Colonnes :** `id`, `category_id?` (NULL = commun), `slug`, `name`,
  `is_active`, `sort_order`, `metadata jsonb`.
- **Relations :** N‑1 `service_categories` ; 1‑N `questions`.
- **RLS :** lecture authentifiée (actifs) ; écriture admin.

#### `questions`
- **Rôle :** une question dynamique.
- **Colonnes :** `id`, `set_id`, `key` (stable, utilisé dans `details`),
  `type question_type`, `label_key` (→ `content_strings`) ou `label`,
  `help_key?`, `placeholder?`, `sort_order`, `is_active`,
  `visible_when jsonb` (§12), `required_when jsonb` (§12),
  `validation jsonb` (min/max/regex/maxPhotos…), `metadata jsonb`.
- **Relations :** N‑1 `question_sets` ; 1‑N `question_options`.
- **Index :** `(set_id, sort_order)`, `unique(set_id, key)`.
- **Contraintes :** `type` ∈ enum ; `key` slug.
- **RLS :** lecture authentifiée (actives) ; écriture admin.
- **Edge Functions :** validation serveur à la soumission (`submit`/transition).
- **Écrans :** C‑09/C‑10 (rendu), AD‑05 (édition).
- **Règles :** BR‑030→034 (infos), BR‑180→182 (photos/docs via type).
- **💡 Généricité :** couvre questions, ordre, conditions d'affichage, obligation
  contextuelle, docs/photos, validation — **sans code ni colonne par question**.

#### `question_options`
- **Rôle :** options des questions `select`/`multiselect`.
- **Colonnes :** `id`, `question_id`, `value`, `label_key?|label`, `sort_order`,
  `is_active`.
- **Relations :** N‑1 `questions`. **RLS :** lecture authentifiée ; écriture admin.

### 3.12 Moteur de notifications 🔜
#### `notification_templates`
- **Rôle :** modèle éditable d'une notification (par type & audience).
- **Colonnes :** `key`, `audience ('client'|'operator'|'admin')`,
  `title_key`/`title`, `body_key`/`body`, `deep_link_template?`,
  `channel ('push'|'inapp'|'both')`, `is_active`, `metadata jsonb` —
  **PK `(key, audience)`** (i18n via `content_strings`).
- **RLS :** lecture serveur/admin ; écriture admin.
- **Edge Functions :** `send-push`.
- **Écrans :** AD‑10.

#### `notification_triggers`
- **Rôle :** **quel événement** déclenche **quel template** (mapping éditable).
- **Colonnes :** `id`, `event_key` (ex. `mission.status.accepted`),
  `template_key`, `audience`, `condition jsonb?`, `is_active`, `sort_order`.
- **RLS :** lecture serveur/admin ; écriture admin.
- **Edge Functions :** Database Webhook → `send-push`.
- **Règles :** `NOTIFICATIONS.md` (catalogue), SPEC §6.
- **💡 Généricité :** ajouter/retirer une notification = donnée, pas de `switch`.

### 3.13 `mission_transitions` 🔜 *(machine à états en donnée)*
- **Rôle :** couples autorisés `(from, to, rôles)` lus par `transition_mission`.
  Les **effets** restent en code (typés/testés).
- **Colonnes :** `id`, `from_status mission_status`, `to_status mission_status`,
  `allowed_roles user_role[]`, `is_active`, `note?`.
- **Index :** `unique(from_status, to_status)`.
- **RLS :** lecture serveur/admin ; écriture admin.
- **Edge Functions / DB :** `transition_mission()` (validation).
- **Écrans :** OP‑04/05/06, AD (visualisation workflow).
- **Règles :** SPEC §2.7 (allow‑list), P1 (rôles décideurs).

### 3.14 Moteur de classification 🔜 *(principe fondateur : besoin libre → service)*
> Transforme un **texte libre** (« mon pneu est crevé ») en **service** de la
> taxonomie, puis déclenche le bon `question_set`. **Entièrement piloté par la
> donnée** : l'admin « apprend » au moteur en ajoutant des indices, sans code.
> Décision **jamais** finale sans validation humaine (l'opérateur peut
> re‑classer en revue).

#### `category_classification`
- **Rôle :** indices d'entraînement/matching d'une catégorie (mots‑clés,
  synonymes, exemples de phrases) pour l'IA **et** un fallback par règles.
- **Colonnes :** `id`, `category_id`, `kind ('keyword'|'synonym'|'example'|'regex')`,
  `value`, `weight`, `locale?`, `is_active`.
- **Relations :** N‑1 `service_categories`.
- **Index :** `(category_id)`, `(kind)`, trigram/GIN sur `value` (matching).
- **RLS :** lecture serveur ; écriture admin.
- **Edge Functions :** `classify-request` (IA + règles).
- **Écrans :** AD‑05 (édition), C‑07 (indirect). 
- **💡 Généricité :** ajouter un métier = insérer catégorie + indices + questions ;
  le moteur s'adapte **sans redéploiement**.

#### Classification (fonctionnement)
- `classify-request` (Edge) reçoit le texte libre → propose **1..N catégories
  candidates** avec score (IA guidée par `category_classification` + règles).
- Si confiance ≥ seuil (`app_config.classification.min_confidence`) → catégorie
  retenue ; sinon **désambiguïsation** (question au client ou choix opérateur).
- Le résultat (catégorie, score, alternatives) est stocké sur la demande
  (`missions.metadata.classification`) ; **modifiable par l'opérateur** en revue.
- Paramètres IA (modèle, seuils, garde‑fous) en **`app_config`** (`classification.*`).

---

## 4. Couche Cœur — Missions & cycle de vie

### 4.1 `missions` 🔜
- **Rôle :** l'objet central ; machine à états (source de vérité).
- **Colonnes clés :**
  - identité : `id`, `client_id`, `operator_id?`, `category_id?`, `family`,
    `status mission_status`.
  - **origine conversationnelle** : `conversation_id?` (demande d'origine),
    `group_id?` (regroupe les missions issues d'une même demande multi‑services),
    `sequence?` (ordre dans le groupe), `depends_on_mission_id?` (dépendance
    d'enchaînement). Cf. `CONVERSATION_ENGINE.md` §7.
  - contenu : `title?`, `free_text?`, `instructions?`, **`details jsonb`**
    (réponses aux questions dynamiques = slots remplis), `metadata jsonb`
    (dont `classification`).
  - localisation : `dropoff_address?`, `dropoff_point geography`,
    `pickup_point? geography`.
  - tarif (snapshots) : `estimated_price?`, `estimated_eta_min?`, `service_fee?`,
    `advance_estimate?`, `advance_actual?`, `final_amount?`, `operator_earning?`.
  - **revue** : `submitted_at?`, `reviewed_at?`, `reviewed_by?`, `review_reason?`.
  - cycle : `accepted_at?`, `completed_at?`, `cancelled_at?`,
    `cancelled_by cancel_actor?`, `cancel_reason?`, `scheduled_for?`,
    `queue_position?`.
  - timestamps.
- **Relations :** N‑1 `profiles` (client), `operator_profiles`,
  `service_categories`, `addresses`, **`conversations`** ; auto‑référence
  `depends_on_mission_id` ; 1‑N `mission_items`, `mission_events`,
  `mission_tracks`, `messages`, `tips` ; 1‑0..1 `quotes`, `payments`, `ratings`,
  `disputes`.
- **Index :** `client_idx`, `operator_idx`, `status_idx`, `created_idx desc`,
  GIST `dropoff_point` ; partiel `status='pending_review'` (file de revue) ;
  `conversation_idx`, `group_idx`.
- **Contraintes :** FK ; `client_id on delete restrict`.
- **RLS :** client = ses missions ; operator = les siennes **+** la file
  `pending_review` (revue) ; admin total. Transitions via
  `transition_mission` (SECURITY DEFINER), **jamais** UPDATE direct du statut.
- **Edge Functions :** `estimate-price`, `assign-mission`, `transition_mission`,
  paiement (`authorize`/`capture` gated).
- **Écrans :** C‑13→C‑27, OP‑04→OP‑13, AD‑03/04.
- **Règles :** **toutes** (machine à états, contrôle humain, snapshots de prix,
  annulation/échec).
- **💡 Généricité :** `details jsonb` + `metadata jsonb` évitent une table EAV et
  absorbent les besoins futurs sans migration.

### 4.2 `mission_items` 🔜
- **Rôle :** articles structurés (courses).
- **Colonnes :** `id`, `mission_id`, `label`, `quantity`, `notes?`.
- **Relations :** N‑1 `missions` (cascade). **Index :** `mission_idx`.
- **RLS :** participants de la mission (client/operator) + admin.
- **Écrans :** C‑09, OP‑06. **Règles :** courses/pharmacie.
- **💡 Note :** conservée (liste structurée éditable) distincte de `details jsonb`
  (réponses libres) — les deux ont des usages différents.

### 4.3 `mission_events` 🔜 *(audit du cycle de vie mission)*
- **Rôle :** journal immuable des transitions.
- **Colonnes :** `id`, `mission_id`, `from_status?`, `to_status`, `actor_id?`,
  `actor_role?`, `metadata jsonb` (motif, `review_reason`, `cancel_reason`…),
  `created_at`.
- **Relations :** N‑1 `missions`. **Index :** `(mission_id)`,
  candidat **partitionnement mensuel** (volume).
- **RLS :** participants + admin (lecture) ; écriture via `transition_mission`.
- **Edge Functions :** `transition_mission` (insert), `send-push` (source).
- **Écrans :** C‑18 (timeline), AD‑04. **Règles :** BR‑224 (traçabilité).

### 4.4 `quotes` 🔜 *(prix proposé — demande libre)*
- **Rôle :** enregistre le **prix fixé par l'opérateur à l'acceptation** d'une
  `custom` (plus lié à des états `quote_*`, supprimés).
- **Colonnes :** `id`, `mission_id`, `operator_id?`, `price`, `eta_min`, `note?`,
  `status quote_status` (`proposed`/`accepted`/`expired`/`cancelled`),
  `expires_at`, `created_at`.
- **Relations :** N‑1 `missions`. **Index :** `mission_idx`.
- **RLS :** participants + admin.
- **Edge Functions :** revue (`transition_mission` acceptation), cron expiration.
- **Écrans :** OP‑05 (saisie), C‑17 (paiement). **Règles :** BR‑016, §6 (24 h).

### 4.5 Conversations (moteur conversationnel) 🔜
> Cœur produit — cf. `CONVERSATION_ENGINE.md`. Réutilise le moteur de questions
> comme **schéma de slots** (pas de table « slot »).

#### `conversations`
- **Rôle :** session de dialogue de constitution d'une demande ; **porte l'état**
  (reprise + contexte).
- **Colonnes :** `id`, `client_id`, `status conversation_status`, `state jsonb`
  (slots remplis, position, intentions retenues), `plan jsonb` (mission(s)
  proposée(s), ordre/dépendances), `detected_intents jsonb`, `locale`,
  `metadata jsonb`, `created_at`, `updated_at`, `expires_at`.
- **Relations :** N‑1 `profiles` ; 1‑N `conversation_turns` ; 1‑N `missions`
  (une conversation → 1..N missions via `conversation_id`/`group_id`).
- **Index :** `(client_id)`, `(status)`, `(expires_at)`.
- **RLS :** propriétaire (client) ; opérateur/admin **lecture** pour la revue.
- **Edge Functions :** `classify-request`, `converse`, `submit-request`.
- **Écrans :** C‑07→C‑13 (dialogue), C‑15 (reprise sur `needs_information`),
  OP‑05 (transcript en revue).
- **Règles :** BR‑CE‑* ; P0/P1.

#### `conversation_turns`
- **Rôle :** historique **immuable** des tours (audit + contexte). **Distinct de
  `messages`** : `conversation_turns` = dialogue de **constitution** (client ↔
  moteur/IA, avant/pendant `pending_review`/`needs_information`) ; `messages` =
  **chat d'exécution** (client ↔ intervenant, mission active).
- **Colonnes :** `id`, `conversation_id`, `role ('user'|'assistant'|'system')`,
  `content text`, `media jsonb?`, `intent_ref?`, `slot_key?`, `extracted jsonb?`,
  `created_at`.
- **Relations :** N‑1 `conversations`. **Index :** `(conversation_id, created_at)`.
- **RLS :** participants + admin. **Edge Functions :** `converse`.
- **💡 Généricité :** les **slots** = `questions` ; les **valeurs** = `state`
  puis `missions.details` → aucune table EAV de réponses.

### 4.6 `disputes` 🔜 *(nouveau — litiges)*
- **Rôle :** litige lié à une mission (traçable, arbitrable).
- **Colonnes :** `id`, `mission_id`, `opened_by`, `opened_role`, `reason`,
  `status dispute_status`, `resolution?`, `resolved_by?`, `refund_amount?`,
  `metadata jsonb`, `created_at`, `resolved_at?`.
- **Relations :** N‑1 `missions`, N‑1 `profiles` (opened_by).
- **Index :** `(mission_id)`, `(status)`.
- **RLS :** parties + admin ; **résolution admin uniquement**.
- **Edge Functions :** `refund` (sim), agrégation preuves.
- **Écrans :** AD‑09 (+ point d'entrée client). **Règles :** BR‑170→173.

---

## 5. Couche Paiement (simulée V1, Stripe‑ready)

### 5.1 `payment_methods` 🔜 (V1 : cartes fictives)
- `id`, `user_id`, `provider_ref` (`sim_pm_*`/`pm_*`), `brand?`, `last4?`,
  `exp_month?`, `exp_year?`, `is_default`, timestamps.
- **RLS :** propriétaire. **Écrans :** C‑17, C‑29. **Règles :** §5 SPEC.

### 5.2 `payments` 🔜
- **Rôle :** 1 paiement par mission ; miroir fidèle du cycle Stripe (simulé).
- **Colonnes :** `id`, `mission_id`, `client_id`, `provider ('mock'|'stripe')`,
  `provider_pi_ref?`, `provider_customer_ref?`, `amount_authorized?`,
  `amount_captured?`, `currency`, `status payment_status`, `authorized_at?`,
  `metadata jsonb`, timestamps.
- **Relations :** N‑1 `missions`/`profiles`. **Index :** `mission_idx`.
- **RLS :** client (lecture), admin ; **écriture Edge Functions (service_role)**.
- **Edge Functions :** `PaymentProvider` (`authorize` **gated `accepted`**,
  `capture`, `void`, `refund`).
- **Écrans :** C‑17, C‑22, AD‑04/09. **Règles :** §5 BUSINESS_RULES, BR‑210→216.

### 5.3 `advances` 🔜 *(avances de frais)*
- `id`, `mission_id`, `operator_id`, `amount`, `receipt_url`, `reimbursed`,
  `created_at`.
- **Contraintes :** `receipt_url` requis pour capturer (BR‑145) — appliqué
  côté logique/Edge (jamais capture sans preuve).
- **RLS :** intervenant (lecture) + admin ; écriture serveur.
- **Écrans :** OP‑07, OP‑11. **Règles :** BR‑140→145.

### 5.4 `tips` 🔜 (V1 simulé) · 5.5 `payouts` 🅥2 · 5.6 `promo_codes` 🅥2
- `tips` : `id`, `mission_id`, `amount`, `provider_ref?`, `created_at` — sim.
- `payouts`/`promo_codes` : structure prête, **non activée** en V1.
- **Règles :** BR‑215 (pourboire sim) ; V2 pour le reste.

---

## 6. Couche Temps réel

### 6.1 `operator_locations` 🔜
- **Rôle :** dernière position connue (1 ligne/intervenant, upsert peu fréquent).
- **Colonnes :** `operator_id pk`, `location geography(point)`, `heading?`,
  `speed?`, `updated_at`.
- **Index :** GIST `location`.
- **RLS :** l'intervenant écrit la sienne ; le **client de la mission active** lit ;
  admin total.
- **Edge Functions / RT :** Broadcast (live) ; upsert périodique.
- **Écrans :** C‑19, OP‑05 (dashboard). **Règles :** `GPS_TRACKING.md`.
- **⚠️ Rappel archi :** le flux **haute fréquence** passe par **Broadcast**, pas
  par cette table (scalabilité).

### 6.2 `mission_tracks` 🔜
- **Rôle :** tracé **échantillonné** (preuve/historique).
- **Colonnes :** `id`, `mission_id`, `point geography`, `recorded_at`.
- **Index :** `(mission_id, recorded_at)` ; **partitionnement mensuel** candidat.
- **RLS :** participants + admin. **Écrans :** C‑19, AD‑04. **Règles :** GPS.

---

## 7. Couche Communication

### 7.1 `messages` 🔜
- **Rôle :** **chat d'exécution** (client ↔ intervenant, mission active). Distinct
  de `conversation_turns` (constitution du besoin, §4.5). La collecte
  d'informations complémentaires en `needs_information` se fait via la
  **conversation** (moteur), pas via ce chat.
- **Colonnes :** `id`, `mission_id`, `sender_id`, `body`, `read_at?`,
  `metadata jsonb` (modération), `created_at`.
- **Index :** `(mission_id, created_at)` ; **partitionnement** candidat.
- **RLS :** **participants de la mission uniquement** ; insert réservé aux 2.
- **Edge Functions / RT :** Postgres Changes ; modération (`CHAT.md`).
- **Écrans :** C‑15, C‑20, OP‑10. **Règles :** BR‑222 (modération).

### 7.2 `notifications` 🔜
- **Rôle :** notifications in‑app (miroir des push).
- **Colonnes :** `id`, `user_id`, `type` (= `notification_templates.key`),
  `title`, `body?`, `mission_id?`, `read_at?`, `metadata jsonb`, `created_at`.
- **Index :** `(user_id, created_at desc)` ; partitionnement candidat.
- **RLS :** destinataire uniquement ; écriture serveur.
- **Edge Functions :** `send-push`. **Écrans :** C‑28. **Règles :** SPEC §6.

---

## 8. Couche Avis & transverse

### 8.1 `ratings` 🔜
- `id`, `mission_id (unique)`, `client_id`, `operator_id`, `stars 1..5`,
  `tags text[]`, `comment?`, `created_at`.
- **RLS :** client écrit le sien ; lecture publique agrégée (via `rating_avg`).
- **Trigger :** recalcul `operator_profiles.rating_avg/count`.
- **Écrans :** C‑23, OP‑12. **Règles :** avis **facultatif** (SPEC).

### 8.2 `audit_log` 🔜 *(nouveau — traçabilité admin générique)*
- **Rôle :** journal **générique** de tous les changements sensibles (catalogue,
  tarifs, config, rôles, remboursements exceptionnels).
- **Colonnes :** `id`, `actor_id?`, `actor_role?`, `table_name`, `row_id?`,
  `action ('insert'|'update'|'delete'|'custom')`, `diff jsonb`, `context jsonb`,
  `created_at`.
- **Index :** `(table_name, row_id)`, `(actor_id, created_at)`.
- **RLS :** **admin** lecture ; écriture serveur (triggers/Edge).
- **Écrans :** AD (audit). **Règles :** BR‑224.
- **💡 Généricité :** **une** table remplace un historique par entité.

### 8.3 Versionnement de configuration 🔜 *(cf. `CONFIG_VERSIONING.md`)*
> Versionne **toute la configuration** (pas les données opérationnelles).
> Générique via un **registre** : ajouter un module = 1 ligne, sans code.

#### `config_modules` (registre)
- **Rôle :** déclare les tables de configuration versionnées.
- **Colonnes :** `key` (pk), `table_name` (unique), `natural_key`,
  `apply_order int`, `schema jsonb?`, `soft_delete_column?`, `is_active`,
  `description?`.
- **RLS :** admin. **💡** ajouter un module de config = insérer une ligne.

#### `config_versions`
- **Colonnes :** `id`, `label`, `status config_version_status`, `notes?`,
  `parent_version_id?`, `created_by`, `created_at`, `validated_by?`,
  `validated_at?`, `published_by?`, `published_at?`, `checksum?`, `metadata jsonb`.
- **Index :** partial `unique where status='published'` (une seule version active).
- **RLS :** admin.

#### `config_snapshots`
- **Rôle :** snapshot JSONB d'un module pour une version (agnostique du schéma).
- **Colonnes :** `id`, `version_id`, `module_key`, `payload jsonb`, `row_count`,
  `created_at`. **Index :** `unique(version_id, module_key)`. **RLS :** admin.
- **Edge Functions :** `config-create-draft`, `config-validate`,
  `config-publish`, `config-rollback` (bornées au registre).
- **Écrans :** AD‑26. **Règles :** admin ; garde‑fous P0/P1/RLS non versionnables.
- **💡 Généricité :** stockage JSONB → nouvelle table de config versionnable
  **sans migration** du système de versions ; upsert par `natural_key`
  (PK stables) + soft‑delete → **intégrité opérationnelle préservée** au rollback.

---

## 9. Enums

| Enum | Valeurs | Statut |
|---|---|---|
| `user_role` | client, operator, admin | ✅ |
| `mission_family` | shopping, auto, home_service, courier, custom | ✅ |
| `mission_status` | created, pending_review, needs_information, rejected, accepted, assigned, **shopping**, preparing, en_route, arrived, in_progress, completed, rated, cancelled, failed *(searching = réservé multi‑op)* | 🔜 |
| `payment_status` | requires_payment_method, requires_capture, processing, succeeded, partially_captured, refunded, failed, canceled | 🔜 |
| `operator_status` | offline, available, busy, paused | 🔜 |
| `quote_status` | proposed, accepted, expired, cancelled | 🔜 |
| `cancel_actor` | client, operator, system | 🔜 |
| `dispute_status` | open, investigating, resolved_refund, resolved_rejected, cancelled | 🔜 |
| `question_type` | text, number, boolean, select, multiselect, photo, document, address, date, time | 🔜 |
| `conversation_status` | active, submitted, abandoned, expired | 🔜 |
| `config_version_status` | draft, validated, published, archived | 🔜 |

> **💡** Les valeurs *métier* extensibles (types de supplément, canaux, actions
> d'audit) sont des **textes** (avec `content_strings`/`app_config`), pas des enums,
> pour éviter des `ALTER TYPE` fréquents. Les enums sont réservés aux **machines à
> états** et rôles (sécurité).

---

## 10. ERD (vue d'ensemble)

```
auth.users 1─1 profiles 1─1 operator_profiles 1─1 operator_locations
                 │  ├──< addresses   ├──< advances/payouts   └──< ratings
                 │  ├──< device_tokens
                 │  └──< notifications
profiles(client) 1 ─< conversations 1─< conversation_turns
profiles(client) 1 ─< missions >─ 1 operator_profiles
   conversations 1─< missions (conversation_id ; group_id regroupe le multi‑services)
   missions 1─< mission_items | mission_events | mission_tracks | messages | tips
   missions 1─0..1 quotes | payments | ratings | disputes
service_categories 1─< missions ; 1─< category_workflow ; 1─< category_classification ;
                   1─< question_sets 1─< questions 1─< question_options
coverage_zones 1─< service_windows ; 1─< pricing_rules ; ⊃ addresses/points
config: app_config (params + feature.* flags) · pricing_modifiers · content_strings ·
        notification_templates · notification_triggers · mission_transitions · audit_log
```

---

## 11. Synthèse « données plutôt que code » (votre demande)

| Comportement | Piloté par | Ajouter/changer sans code ? |
|---|---|---|
| **Dialogue de collecte du besoin** | `conversations` + moteur de questions (slots) + `content_strings` + `app_config` (`conversation.*`) | ✅ (flux déterministe sur données) |
| **Classer un besoin libre → service** | `classify-request` + `category_classification` + `app_config` (`classification.*`) | ✅ (ajouter un métier = données) |
| Catalogue (taxonomie), prix, zones, horaires | tables dédiées | ✅ |
| Étapes d'une mission | `category_workflow` | ✅ |
| Transitions autorisées | `mission_transitions` | ✅ (effets = code) |
| Questions, ordre, conditions, obligation, docs/photos, validation | moteur de questions | ✅ |
| Notifications (déclencheurs & textes) | `notification_triggers` + `templates` + `content_strings` | ✅ |
| Messages/labels/erreurs/mentions | `content_strings` | ✅ |
| Suppléments tarifaires | `pricing_modifiers` | ✅ |
| Délais, limites, constantes | `app_config` | ✅ |
| Activation de fonctionnalités | `app_config` (clés `feature.*`) | ✅ |
| Traçabilité | `audit_log` (générique) | ✅ |

## 12. Mini‑langage de conditions (borné)

Utilisé par `visible_when`, `required_when`, `pricing_modifiers.condition`,
`notification_triggers.condition`. **JSON déclaratif, non Turing‑complet.**

```json
{ "all": [ { "==": ["answer.has_fridge", true] },
           { "in": ["answer.size", ["L","XL"]] } ] }
```
Opérateurs autorisés : `all`, `any`, `not`, `==`, `!=`, `>`, `>=`, `<`, `<=`,
`in`, `exists`. Contexte exposé : `answer.*` (réponses), `mission.*`, `now`,
`zone.*`. Évalué par une fonction serveur **sûre** (liste blanche d'opérateurs),
jamais `eval`.

---

## 13. Impacts sur le socle déjà livré

- `service_categories` (M1.1) : retirer `requires_shopping`/`requires_preparation`
  au profit de `category_workflow` (migration à la reprise ; aucune dépendance).
- Ajouter `metadata jsonb` à `profiles` (socle) via migration légère.
- Enums `mission_status` etc. : créés à la reprise avec les valeurs §9.
- `app_config` : créé à M1.3 (clés de BUSINESS_RULES §0.3).
- Tout le reste = `🔜 à construire`, sans contredire l'existant.

## 14. Cohérence

- États, notifications, gate paiement, rôles décideurs : **alignés** avec
  SPEC/BUSINESS_RULES/PRD/UX.
- `disputes` et les clés `app_config` (issues de BUSINESS_RULES) sont **intégrées**
  ici (levée des « ajouts à consolider »).
- Généralisations (`category_workflow`, `mission_transitions`, questions,
  templates, `content_strings`, `audit_log`) : **nouvelles** vs architecture v1.0,
  cohérentes avec son esprit (data‑driven, RLS partout). Documentées comme
  extensions, pas comme contradictions.

## 15. Références

`PRD.md` · `BUSINESS_RULES.md` · `SPEC_FONCTIONNELLE_V1.md` · `UX_SPEC.md` ·
`Architecture_Technique.md` · à venir : `API_SPEC.md`, `ADMIN_PANEL.md`,
`GPS_TRACKING.md`, `NOTIFICATIONS.md`, `CHAT.md`.
