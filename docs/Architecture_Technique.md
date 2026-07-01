# Architecture technique — `[NOM_PRODUIT]`
## Plateforme de traitement de demandes de services & livraisons à la demande

> **Version :** 2.0 — **document consolidé** (source de vérité technique unique).
> Cette version **remplace** toute version antérieure et **n'a pas d'amendement** :
> toutes les décisions prises depuis le début y sont intégrées directement. Un
> développeur peut la lire **seule** pour comprendre l'architecture.
>
> **Stack :** React Native + Expo · Supabase (PostgreSQL + PostGIS, Auth,
> Realtime, Storage, Edge Functions) · IA (classification + conversation) ·
> Paiement **simulé** (interface Stripe‑ready) · Push Expo · Géoloc temps réel.
>
> **Documents liés (autorités par domaine) :** `PRD.md` (intention),
> `SPEC_FONCTIONNELLE_V1.md` (règles fonctionnelles), `BUSINESS_RULES.md` (règles
> métier), `DATA_MODEL.md` (schéma détaillé — **fait foi** pour les tables),
> `API_SPEC.md` (contrats d'API — **fait foi**), `UX_SPEC.md` (écrans),
> `CONVERSATION_ENGINE.md` (moteur conversationnel — **fait foi**).

---

## SOMMAIRE
1. Vue d'ensemble & principes fondateurs
2. Schéma d'architecture
3. Justification de la stack
4. Composants & services
5. Rôles & modèle d'autorisation
6. Architecture des données (domaines, enums, moteurs pilotés par la donnée)
7. Machine à états de la mission (validation humaine)
8. Moteur conversationnel & classification
9. Sécurité (RLS)
10. Surface d'API (PostgREST · RPC · Edge Functions · Realtime)
11. Géolocalisation temps réel
12. Conversation vs chat
13. Paiement simulé (Stripe‑ready)
14. Notifications (pilotées par la donnée)
15. Stockage des images
16. Flux de données détaillés
17. Scalabilité & performance
18. Sécurité & conformité (RGPD)
19. DevOps, environnements & CI/CD
20. Roadmap technique
21. Décisions ouvertes

---

## 1. Vue d'ensemble & principes fondateurs

L'application est un **moteur de traitement de demandes** : l'utilisateur décrit
librement son besoin, un moteur conversationnel (IA + règles, **piloté par la
donnée**) le comprend et le complète, puis **un opérateur humain valide** avant
toute création de mission et tout paiement. Le backend repose sur **Supabase**
(BaaS) : pas de serveur applicatif maison ; PostgreSQL reste la source de vérité,
la logique sensible vit dans des **Edge Functions**.

**Principes fondateurs (non négociables) :**

- **P0 — Moteur de demandes, pas de catalogue.** L'utilisateur **ne choisit
  jamais** de catégorie. Il décrit son besoin (« De quoi avez‑vous besoin
  aujourd'hui ? ») ; le système **classe** et **guide**. Ajouter un métier =
  **enrichir les données**, jamais réécrire l'app.
- **P1 — Contrôle humain total.** Aucune mission créée ni payée automatiquement.
  L'IA **prépare**, l'**opérateur décide** (accepter / refuser / demander des
  infos). Le client ne dépasse jamais `pending_review` de sa propre initiative et
  **ne paie jamais avant acceptation**.
- **P2 — Tout piloté par la donnée.** Catalogue, questions, workflows,
  transitions, tarifs, notifications, textes, seuils, flags vivent en base et sont
  **administrables sans redéploiement**. Le code est un **moteur générique**.
- **P3 — Sécurité par défaut.** RLS activée sur **toutes** les tables, refus par
  défaut ; `service_role` (contourne la RLS) **uniquement** côté serveur.
- **P4 — La base est la source de vérité.** La machine à états vit en base ; tout
  réagit aux transitions (triggers, Realtime).
- **P5 — Construire pour une flotte, opérer avec une personne.** Multi‑intervenant
  dès le schéma ; V1 opérée en mono‑intervenant.
- **P6 — Éphémère vs persistant.** La position GPS haute fréquence passe par
  **Realtime Broadcast** (pas d'écriture DB par tick) — clé de la scalabilité.

---

## 2. Schéma d'architecture

```
┌───────────────────────────────────────────────────────────────┐
│                     APPLICATIONS MOBILES (iOS d'abord)         │
│        React Native + Expo (1 base de code, 2 expériences)     │
│   ┌──────────────────┐        ┌──────────────────────────┐     │
│   │   App CLIENT     │        │  App OPÉRATEUR (cockpit)  │     │
│   │  dialogue libre  │        │  revue + réalisation      │     │
│   └──────────────────┘        └──────────────────────────┘     │
│  Maps SDK · Expo Notifications · Realtime JS · (Paiement sim)  │
└───────────────┬───────────────────────────────┬───────────────┘
                │  HTTPS / WSS (JWT)             │
                ▼                               ▼
┌───────────────────────────────────────────────────────────────┐
│                          SUPABASE                              │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌────────────────┐  │
│  │  Auth    │ │ PostgreSQL │ │ Realtime │ │    Storage     │  │
│  │ (JWT,    │ │ + RLS      │ │ Broadcast│ │ (buckets img)  │  │
│  │ phone/   │ │ + PostGIS  │ │ Presence │ │                │  │
│  │ Apple)   │ │ + triggers │ │ Changes  │ │                │  │
│  └──────────┘ └─────┬──────┘ └──────────┘ └────────────────┘  │
│  ┌──────────────────┴─────────────────────────────────────┐  │
│  │            EDGE FUNCTIONS (Deno, service_role)           │  │
│  │  classify-request · converse · zone-check · estimate-   │  │
│  │  price · submit-request · review-request · create-      │  │
│  │  authorization · capture-payment · refund · assign-     │  │
│  │  mission · send-push        (+ RPC transition_mission)   │  │
│  └───────┬───────────────────────────────┬────────────────┘  │
│  pg_cron · pg_net · Database Webhooks · Vault (secrets)       │
└──────────┬───────────────┬───────────────┬───────────────────┘
           ▼               ▼               ▼
   ┌──────────────┐ ┌────────────────┐ ┌──────────────┐
   │  IA / LLM    │ │ Expo Push (FCM/ │ │ Maps Provider│
   │ (classif. +  │ │  APNs)         │ │ (Google/     │
   │ conversation)│ │                │ │  Mapbox)     │
   │  BORNÉE      │ │                │ │              │
   └──────────────┘ └────────────────┘ └──────────────┘
       (Paiement réel Stripe : V2, derrière PaymentProvider)
```

---

## 3. Justification de la stack

| Technologie | Pourquoi |
|---|---|
| **React Native + Expo** | Une base de code, deux apps (client + cockpit), iOS d'abord ; EAS Build/Submit/Update (OTA). Écosystème mûr : `expo-location`, `expo-notifications`, cartes. |
| **Supabase** | Élimine le serveur à maintenir tout en gardant **PostgreSQL** (pas de lock‑in). Auth, base, **Realtime**, **Storage**, **Edge Functions**, **RLS** en un produit. Open‑source, migrable. |
| **PostgreSQL (+PostGIS/pg_cron/pg_net/pgcrypto)** | Transactions ACID (missions/paiements), machines à états fiables, **RLS** native (pilier sécurité), géo (PostGIS), planifié (pg_cron), HTTP sortant (pg_net). |
| **IA (classification + conversation)** | Comprendre un besoin en langage naturel et **assister** le dialogue — **bornée** : elle propose, le moteur déterministe et l'opérateur décident. Modèle/seuils en `app_config` (remplaçable sans refonte). |
| **Paiement simulé (interface `PaymentProvider`)** | V1 sans paiement réel ; simulation **fidèle** (autorisation/capture/remboursement). Stripe (capture manuelle) se branche en V2 **sans refonte**. |
| **Expo Push** | Abstraction APNs/FCM ; déclenché par les transitions d'état (Database Webhook → `send-push`), textes **pilotés par la donnée**. |
| **Realtime Broadcast** | Suivi live fluide et scalable **sans écrire en base à chaque tick**. |
| **Supabase Storage** | Photos de demande, tickets, preuves, avatars, documents — buckets privés à politiques par mission/propriétaire, URLs signées. |

---

## 4. Composants & services

### 4.1 Auth
- OTP **téléphone** + **Sign in with Apple** (Google prêt pour la V2, purement
  déclaratif). JWT à claims personnalisés : le **rôle** est injecté par un
  **Custom Access Token Hook** (§5) → lu par la RLS sans requête supplémentaire.

### 4.2 PostgreSQL (+ extensions)
- `postgis`, `pgcrypto`, `pg_cron`, `pg_net`, `uuid-ossp`.
- Triggers : journalisation des transitions, `updated_at`, webhooks (push).
- Fonctions `SECURITY DEFINER` pour la logique transactionnelle critique
  (`transition_mission`, création de profil, etc.).

### 4.3 Realtime
- **Broadcast** : positions GPS live, indicateurs de frappe.
- **Presence** : disponibilité intervenant.
- **Postgres Changes** : transitions de mission, nouveaux messages, **file de revue**.

### 4.4 Storage
- Buckets **privés** : `request-photos`, `mission-proofs`, `avatars`, `documents`.
  Accès par politiques (scoping mission/propriétaire), URLs signées.

### 4.5 Edge Functions (Deno) — logique sensible
| Fonction | Rôle | Appelée par |
|---|---|---|
| `classify-request` | texte libre → intentions candidates (IA + `category_classification`) | app (accueil) |
| `converse` | tour de dialogue : extraction + prochaine question (IA + moteur déterministe) | app (dialogue) |
| `zone-check` | couverture + horaires (PostGIS) | app |
| `estimate-price` | prix + ETA (tarifs en base) | app |
| `submit-request` | validation serveur + création de 1..N missions → `pending_review` | app |
| `review-request` | **décision opérateur** : accepter/refuser/demander des infos (prix si `custom`) | cockpit |
| `create-authorization` | **paiement simulé** — autorisation, **gaté `accepted`** | app (après acceptation) |
| `capture-payment` | capture du montant réel à la clôture | cockpit |
| `refund` | remboursement/annulation (sim) | cockpit/admin |
| `assign-mission` | affectation (V1 auto ; V2 dispatch) | trigger/serveur |
| `send-push` | notifications Expo (templates en base) | Database Webhook |

RPC Postgres : **`transition_mission`** (`SECURITY DEFINER`) valide et applique
les transitions d'exécution (allow‑list en base). **Aucune fonction
`create-payment-intent`/`compose-quote`/`stripe-webhook` en V1** : la première est
remplacée par `create-authorization`, la deuxième par `review-request`, la
dernière est réservée à la V2 (Stripe réel).

> **Règle d'or :** la clé `service_role` n'existe **que** dans les Edge Functions.
> L'app mobile utilise la clé `anon` + le JWT utilisateur (soumis à la RLS).

### 4.6 Services externes
- **IA / LLM** (classification + conversation), **bornée** ; secrets serveur.
- **Expo Push** (APNs/FCM).
- **Cartes** : Google ou Mapbox (carte, itinéraire, géocodage) — à trancher.
- **Twilio** (OTP SMS + numéro masqué) — **V2** ; appels **simulés** en V1.
- **Stripe** — **V2**, derrière `PaymentProvider`.

---

## 5. Rôles & modèle d'autorisation

| Rôle | Description | Accès |
|---|---|---|
| `client` | décrit des besoins | ses demandes/conversations, adresses, paiements, messages, avis |
| `operator` | **décide** (revue) **et** réalise (V1) | file `pending_review`, missions attribuées, gains/avances/justificatifs, tableau de bord dispatch |
| `admin` | exploitation/support/**administration** | accès étendu (back‑office), gestion **data‑driven** de toute la plateforme, litiges, remboursements |

- **Décision de revue** (`pending_review → accepted|rejected|needs_information`)
  réservée à **`operator`/`admin`** (P1).
- **Rôle en JWT** : table `profiles.role` → **Custom Access Token Hook** injecte le
  claim `user_role` → la RLS lit `auth`‑claims (helper `current_user_role()`), sans
  récursion. Anti‑escalade : un non‑admin ne peut pas changer un rôle.
- **Niveaux d'accès :** app → `anon` + JWT (RLS) ; Edge Functions → `service_role`
  (contourne la RLS pour opérations contrôlées) ; back‑office → `admin` + RLS.

---

## 6. Architecture des données

> **`DATA_MODEL.md` fait foi** pour le détail exhaustif (colonnes, index,
> contraintes, RLS, ~35 tables). Ici : l'**architecture** (domaines, enums,
> moteurs pilotés par la donnée). Conventions : PK `uuid`,
> `created_at`/`updated_at`, `metadata jsonb` sur les entités mutables, RLS partout.

### 6.1 Trois couches
1. **Structure (stable)** — `profiles`, `operator_profiles`, `missions`,
   `payments`, `messages`, `conversations`, `mission_events`…
2. **Configuration & règles (data‑driven)** — `service_categories` (taxonomie),
   `category_workflow`, `category_classification`, `question_sets/questions/
   question_options`, `mission_transitions`, `pricing_rules/pricing_modifiers`,
   `coverage_zones/service_windows`, `notification_templates/notification_triggers`,
   `app_config` (seuils + flags `feature.*`).
3. **Contenu & i18n (éditable)** — `content_strings` (tous les textes affichés).

### 6.2 Domaines (inventaire)
- **Identité** : `profiles`, `operator_profiles`, `device_tokens`, `addresses`.
- **Référentiel/config** : `service_categories`, `category_workflow`,
  `category_classification`, `coverage_zones`, `service_windows`, `waitlist`,
  `pricing_rules`, `pricing_modifiers`, `app_config`, `content_strings`,
  `question_sets`, `questions`, `question_options`, `notification_templates`,
  `notification_triggers`, `mission_transitions`.
- **Conversation** : `conversations`, `conversation_turns`.
- **Cœur** : `missions` (+ `conversation_id`, `group_id`, `sequence`,
  `depends_on_mission_id`, `details jsonb`), `mission_items`, `mission_events`,
  `quotes`, `disputes`.
- **Paiement (sim)** : `payment_methods`, `payments`, `advances`, `tips`
  (`payouts`/`promo_codes` = V2).
- **Temps réel** : `operator_locations`, `mission_tracks`.
- **Communication** : `messages`, `notifications`.
- **Avis & transverse** : `ratings`, `audit_log`.

### 6.3 Enums (machines à états & catégories)
```
user_role           = client | operator | admin
mission_family      = shopping | auto | home_service | courier | custom
mission_status      = created | pending_review | needs_information | rejected |
                      accepted | assigned | shopping | preparing | en_route |
                      arrived | in_progress | completed | rated | cancelled | failed
                      (searching = réservé au dispatch multi‑intervenant, V2)
payment_status      = requires_payment_method | requires_capture | processing |
                      succeeded | partially_captured | refunded | failed | canceled
operator_status     = offline | available | busy | paused
quote_status        = proposed | accepted | expired | cancelled
cancel_actor        = client | operator | system
dispute_status      = open | investigating | resolved_refund | resolved_rejected | cancelled
question_type       = text | number | boolean | select | multiselect | photo |
                      document | address | date | time
conversation_status = active | submitted | abandoned | expired
```
> Les valeurs **métier extensibles** (types de supplément, canaux, actions
> d'audit) sont des **textes** (avec `content_strings`/`app_config`), pas des enums,
> pour éviter des `ALTER TYPE` fréquents. Les enums sont réservés aux machines à
> états et aux rôles (sécurité).

### 6.4 Moteurs pilotés par la donnée
| Comportement | Piloté par |
|---|---|
| Dialogue de collecte du besoin | `conversations` + moteur de questions (slots) + `content_strings` + `app_config` |
| Classer un besoin libre → service | `classify-request` + `category_classification` + `app_config` |
| Étapes d'une mission | `category_workflow` (remplace des booléens) |
| Transitions autorisées | `mission_transitions` (effets = code) |
| Questions/ordre/conditions/obligation/validation/docs | moteur de questions |
| Notifications (déclencheurs + textes) | `notification_triggers` + `notification_templates` + `content_strings` |
| Suppléments tarifaires | `pricing_modifiers` (condition JSON) |
| Seuils, délais, limites, flags | `app_config` (`feature.*`) |
| Traçabilité | `audit_log` (générique) |
| Versionnement de **toute** la configuration (brouillon→validation→publication→rollback) | `config_modules`/`config_versions`/`config_snapshots` (registre générique) — cf. `CONFIG_VERSIONING.md` |

---

## 7. Machine à états de la mission (validation humaine)

> **`SPEC_FONCTIONNELLE_V1.md` §2 fait foi** ; résumé d'architecture ci‑dessous.

```
created (brouillon, dialogue)
  → pending_review        [client soumet]        → push OPÉRATEUR
pending_review
  → accepted              [operator/admin]        → notif client ; PAIEMENT DÉBLOQUÉ
  → rejected              [operator/admin]         (terminal)
  → needs_information     [operator/admin]         → reprise conversation
needs_information → pending_review [client]
accepted
  → (paiement simulé autorisé) → assigned [système ; auto V1]
assigned → [shopping] → [preparing] → en_route → arrived → in_progress → completed → rated
transverses : cancelled | failed
```
- **Toutes** les transitions passent par `transition_mission` (validation contre
  `mission_transitions` + rôle, journalisation `mission_events`). **Jamais** de
  `UPDATE` direct du statut par le client.
- **Multi‑services** : une demande peut produire **plusieurs** missions liées
  (`group_id`, `sequence`, `depends_on_mission_id`) ; chacune suit sa propre
  machine à états, l'opérateur peut les traiter séparément.

---

## 8. Moteur conversationnel & classification

> **`CONVERSATION_ENGINE.md` fait foi.** Points d'architecture :

- **Dialog manager déterministe + IA bornée.** Le **moteur** (code) choisit la
  prochaine question à partir des **données** (`questions`, conditions du
  mini‑langage borné). L'**IA** comprend/extrait/reformule/propose — jamais
  décisionnaire.
- **Classification** : `classify-request` (IA guidée par `category_classification`
  + règles) → intentions candidates ; désambiguïsation si score bas ;
  l'opérateur peut re‑classer en revue (P1).
- **Multi‑intention** → **plan** de mission(s) (`conversations.plan`) : découpage
  en missions / mission enchaînée / **escalade opérateur** si ambigu.
- **Contexte & reprise** : `conversations.state` (structuré) + `conversation_turns`
  (historique) ; reprise à tout moment ; `needs_information` **rouvre** la
  conversation. **Garde‑fous** : options `select` fermées, valeurs revalidées,
  rate‑limit, contexte borné, politique de dialogue **rejouable/testable** sans IA.
- **L'IA s'arrête à `pending_review`** : au‑delà, plus aucune automatisation (P1).

---

## 9. Sécurité (RLS)

- **Toutes** les tables : `ENABLE ROW LEVEL SECURITY`, refus par défaut. `FORCE`
  appliqué là où aucun trigger `SECURITY DEFINER` propriétaire n'écrit (les tables
  à création automatique — `profiles` — restent en `ENABLE` pour laisser le motif
  définisseur fonctionner ; protection inchangée car l'accès applicatif passe par
  `anon`/`authenticated`).
- **Motifs types :** propriétaire (`user_id = auth.uid()`) ; participants de la
  mission (client/operator) ; `admin` via `current_user_role()`. La lecture du
  référentiel est authentifiée ; l'**écriture de configuration est admin**.
- Les transitions critiques (revue, paiement, capture) passent par des **Edge
  Functions**/**`SECURITY DEFINER`**, jamais par un `UPDATE` client — garantit
  atomicité et **P1** (un client ne peut pas se mettre `accepted`/`completed`).
- **Détail des policies : `DATA_MODEL.md`.**

---

## 10. Surface d'API

> **`API_SPEC.md` fait foi pour les contrats.** Architecture :

- **PostgREST (RLS)** : CRUD du référentiel/questions (lecture), adresses,
  missions du client, `conversations`/`conversation_turns` (propriétaire),
  messages, notifications, avis. Écriture de configuration = **admin**.
- **RPC** : `transition_mission` (transitions d'exécution).
- **Edge Functions** : §4.5 (logique sensible/orchestration).
- **Realtime** :
  `mission:{id}:status` (Changes), `mission:{id}:location` (Broadcast),
  `mission:{id}:chat` (Changes), `mission:{id}:typing` (Broadcast),
  `operator:review-inbox` (Changes sur `pending_review`), `operator:presence`.

---

## 11. Géolocalisation temps réel

- **Le piège évité :** écrire chaque position (1/s) et la diffuser via Postgres
  Changes ne passe pas l'échelle.
- **Pattern :** position live via **Broadcast** (éphémère) ; **UPSERT**
  `operator_locations` (dernière position) et **INSERT** `mission_tracks`
  (échantillon toutes ~10–20 s) peu fréquents. Suivi en arrière‑plan via
  `expo-location` (fréquence adaptative, gestion batterie). Détails :
  `GPS_TRACKING.md` (à venir).
- **Calculs géo (PostGIS) :** couverture `ST_Covers(zone.area, point)` ;
  distance/ETA `ST_Distance` (affiné par l'API d'itinéraire) ; plus proche
  intervenant `ORDER BY location <-> point` (dispatch V2, index GIST).

---

## 12. Conversation vs chat (deux canaux distincts)

- **`conversations` / `conversation_turns`** = **constitution** du besoin
  (client ↔ moteur/IA), avant `pending_review` et pendant `needs_information`.
- **`messages`** = **chat d'exécution** (client ↔ intervenant) une fois la mission
  active. Modération anti‑coordonnées + RGPD : `CHAT.md` (à venir).

---

## 13. Paiement simulé (Stripe‑ready)

- **V1 : aucun paiement réel.** Interface **`PaymentProvider`**
  (`authorize` / `capture` / `refund` / `void`) avec une implémentation **mock**
  qui reproduit **fidèlement** le cycle Stripe (capture manuelle) et remplit
  `payments` (références `sim_…`, statuts `requires_capture → succeeded /
  partially_captured → refunded`, `canceled` pour un `void`).
- **Garde‑fou fondamental :** `authorize` est **refusé** tant que
  `status ≠ accepted` (P1) — le client ne paie jamais avant validation humaine.
- **Cycle :** acceptation → `create-authorization` (empreinte + marge +
  `advance_estimate`) → exécution → `capture-payment` (montant réel ≤ autorisé) →
  reçu. Annulation → `void`/`refund`. **Pourboire** V1 **simulé**.
- **V2 :** `StripePaymentProvider` (PaymentIntent capture manuelle, webhook
  `stripe-webhook` signé) remplace le mock **sans changer** la machine à états ni
  les Edge Functions métier. `operator_profiles.stripe_account` prêt (Connect).

---

## 14. Notifications (pilotées par la donnée)

- **Déclenchement :** transition d'état → Database Webhook (pg_net) →
  `send-push` → Expo Push (APNs/FCM), `device_tokens`.
- **100 % data‑driven :** `notification_triggers` (événement → template) +
  `notification_templates` (audience, canal) + `content_strings` (textes i18n).
  Ajouter/modifier une notification = **données**. Catalogue : `NOTIFICATIONS.md`
  (à venir) ; types actuels dans `SPEC_FONCTIONNELLE_V1.md` §6.
- **Règles :** regroupement, silence nocturne (sauf mission active),
  **idempotence** (clé d'événement), deep‑link.

---

## 15. Stockage des images

- **Buckets privés :** `request-photos` (photos de demande), `mission-proofs`
  (tickets, preuves de livraison), `avatars`, `documents` (intervenant/futur).
- **Accès :** politiques sur `storage.objects` (chemin préfixé par
  `mission_id`/`user_id`), **URLs signées**. La policy « participant de la
  mission » sur `mission-proofs` est branchée avec le modèle métier.
- **Upload** direct depuis l'app (compression client) ; **cycle de vie** : purge
  liée aux comptes supprimés (RGPD §18).

---

## 16. Flux de données détaillés

### 16.1 Besoin → dialogue → soumission
```
App Client
  → POST classify-request (texte libre)     [Edge: IA + règles] → intentions
  → POST converse (boucle)                   [Edge: IA + moteur] → questions dynamiques
  → POST zone-check / estimate-price         [Edge: PostGIS / tarifs]
  → POST submit-request                      [Edge] → 1..N missions (pending_review)
                                                    → webhook → send-push (opérateur)
```
### 16.2 Revue humaine → paiement → affectation
```
Cockpit (OP-05) → POST review-request        [Edge] → accepted | rejected | needs_information
  accepté → notif client ; PAIEMENT DÉBLOQUÉ
App Client → POST create-authorization        [Edge: PaymentProvider mock] → requires_capture
           → (auto) assign-mission            → assigned → notif intervenant
```
### 16.3 Exécution → clôture → reçu → avis
```
Cockpit → rpc transition_mission (étapes)     → shopping/preparing/en_route/arrived/in_progress
  → POST capture-payment (montant réel + preuve) [Edge] → succeeded → completed
  → reçu ; notif ; client note (facultatif) → rating_avg recalculé (trigger)
```

---

## 17. Scalabilité & performance

| Levier | Mesure |
|---|---|
| Pooling | **Supavisor** pour absorber les connexions app + Edge. |
| Éphémère vs persistant | Positions live en **Broadcast** (levier #1). |
| Index | GIST sur toutes les colonnes `geography` ; index FK/`status`/`created_at` ; trigram/GIN sur `category_classification.value`. |
| Partitionnement | mensuel sur `mission_tracks`, `messages`, `mission_events`, `notifications`, `conversation_turns`. |
| Realtime ciblé | Postgres Changes seulement sur les tables utiles. |
| Pagination | curseur (`created_at`/id) ; jamais de `SELECT *` non borné. |
| IA maîtrisée | contexte borné, rate‑limit (`app_config`), cache du référentiel. |
| Tâches planifiées | `pg_cron` : expiration devis/conversations, purge tracés, agrégats. |
| Read replicas | lectures analytiques (dashboard admin) sur réplicas. |
| OTA | `EAS Update` pour correctifs sans review App Store. |

---

## 18. Sécurité & conformité (RGPD)

- **RLS partout, refus par défaut** ; `service_role` cantonné aux Edge Functions.
- **Secrets** en **Supabase Vault** / env (IA, cartes, plus tard Stripe/Twilio) —
  jamais dans l'app.
- **Paiement** : aucune donnée de carte réelle en V1 (mock) ; en V2, déléguée à
  Stripe (PCI‑DSS), seules des références stockées.
- **PII** : minimisation ; chiffrement au repos (Supabase) ; **numéro masqué** en
  V2 (Twilio) ; appels **simulés** en V1.
- **Droits RGPD** : suppression de compte (anonymisation des missions
  comptables, purge Storage) ; export ; **rétention configurable** (`app_config`,
  purge `pg_cron`) des positions/messages/transcripts.
- **Audit** : `mission_events` + `audit_log` (changements admin) + logs Edge.
- **IA** : contexte borné, pas de décision autonome, modération anti‑coordonnées.

---

## 19. DevOps, environnements & CI/CD

- **Environnements** : `dev` / `staging` / `prod` (3 projets Supabase).
- **Migrations** : **Supabase CLI** (SQL versionné en Git) ; **données de démo**
  en `seed.sql` (le référentiel étant administrable).
- **Edge Functions** : déploiement CLI, testées en local (Deno).
- **App** : **EAS Build/Submit/Update** (OTA).
- **Secrets** par environnement (jamais commités).
- **Observabilité** : logs Supabase + Edge ; suivi d'erreurs (Sentry) ; métriques.
- **Tests** : Edge Functions (paiement sim, revue, transitions) ; **tests RLS**
  (pgTAP) — un client ne voit jamais la demande d'un autre — à automatiser ;
  **politique de dialogue rejouable** sans IA.

---

## 20. Roadmap technique

| Étape | Contenu | Dépend de |
|---|---|---|
| **T0 — Socle** ✅ | Projet Supabase, extensions, identité/rôles, hook JWT, Storage, squelette Edge Functions | — |
| **M1 — Référentiel & zones** (en cours) | catalogue (taxonomie), zones/horaires, tarifs, `app_config`, `zone-check` | T0 |
| **M2 — Conversation & classification** | `conversations`, `conversation_turns`, moteur de questions, `classify-request`, `converse` | M1 |
| **M3 — Cœur missions** | `missions` + machine à états + `mission_transitions` + `mission_events` + multi‑services | M1/M2 |
| **M4 — Tarification** | `estimate-price`, `pricing_modifiers` | M3 |
| **M5 — Paiement simulé** | `PaymentProvider` (mock), `create-authorization`/`capture`/`refund` | M3/M4 |
| **M6 — Revue & affectation** | `review-request`, `assign-mission`, tableau de bord dispatch | M3 |
| **M7 — Temps réel** | Broadcast, `operator_locations`, `mission_tracks` | M3 |
| **M8 — Chat** | `messages` + Changes + modération | M3 |
| **M9 — Notifications** | `device_tokens`, templates/triggers, `send-push` | M3 |
| **M10 — Storage métier** | policy participant `mission-proofs` | M3 |
| **M11 — Avis** | `ratings` | M3 |
| **M12 — Admin** | back‑office (pilotage data‑driven) | tout |
| **M13 — Durcissement** | tests RLS pgTAP, RGPD, partitionnement, monitoring | tout |
| **V2** | **Stripe réel**, **multi‑intervenant** (dispatch, `payouts`), **Twilio** (OTP + numéro masqué), Google login, Android, mode sombre | post‑V1 |

---

## 21. Décisions ouvertes (à trancher avant l'étape concernée)

1. **Cartes** : Google Maps ou Mapbox.
2. **OTP / numéro masqué** : Twilio (V2) ou alternative.
3. **Marge d'autorisation** paiement (ex. +20 %) — valeur `app_config`.
4. **Suivi en arrière‑plan** intervenant (permissions iOS/review).
5. **Rétention** (positions, messages, transcripts) — valeurs `app_config`.
6. **Nom du produit** (`[NOM_PRODUIT]`).

> Ces points sont des **valeurs de configuration** ou des choix externes ; ils ne
> requièrent **aucune décision d'architecture** en cours de développement.

---

*Fin du document d'architecture consolidé v2.0 — source de vérité technique
unique, cohérente avec l'ensemble de la documentation.*
