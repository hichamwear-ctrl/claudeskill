# Architecture technique complète — `[NOM_PRODUIT]`
## Application de services & livraisons à la demande

> **Version :** 1.0 — Document d'architecture (dérivé du PRD v1.0 et de la Spec UX v1.0)
> **Stack imposée :** React Native + Expo · Supabase · PostgreSQL · Stripe · Push · Géoloc temps réel · Chat · Stockage images
> **Objectif de charge :** plusieurs milliers d'utilisateurs actifs, montée en charge progressive.
> **Principe directeur (rappel PRD §4.3) :** *« Construire pour une flotte, opérer avec une personne. »* Le schéma et le code sont multi-intervenants dès le jour 1 ; seule la réalité opérationnelle est mono-intervenant.

---

## AMENDEMENT v1.1 — Validation opérateur obligatoire (contrôle humain)

> Cet amendement **prévaut** sur le corps du document ci-dessous là où ils
> divergent. Détail complet dans `SPEC_FONCTIONNELLE_V1.md` (§0, §2) et
> `UX_SPEC.md` (§4, §5, §7).

**Règle :** aucune mission n'est créée ni payée automatiquement. Toute demande
passe par une **décision humaine** (`operator`/`admin`) avant acceptation et
avant tout paiement.

Impacts sur ce document :
- **§5 Rôles :** la décision de revue (accepter/refuser/demander des infos) est
  réservée à `operator`/`admin`. Le client ne dépasse jamais `pending_review`.
- **§6.1 Enum `mission_status` :** **ajouter** `pending_review`,
  `needs_information`, `rejected` (+ `shopping`) ; **retirer**
  `quote_pending`/`quote_sent`/`quote_refused` (consolidés dans la revue ; le prix
  d'une demande libre est fixé par l'opérateur à l'acceptation, enregistré dans
  `quotes`, validité 24 h).
- **§6.5 `missions` :** ajouter `submitted_at`, `reviewed_at`, `reviewed_by`,
  `review_reason`.
- **§4.5 Edge Functions :** le corps historique liste des noms **remplacés** —
  `create-payment-intent` → **`create-authorization`** (via `PaymentProvider`,
  gaté `accepted`) ; `compose-quote` → intégré à **`review-request`** (prix fixé à
  l'acceptation). **Nouvelles fonctions** : `classify-request`, `converse`,
  `submit-request`, `review-request`. Contrats détaillés dans `API_SPEC.md` (fait
  foi) ; `stripe-webhook` reste réservé à la V2.
- **§9 / §12 Paiement :** `authorize` est **verrouillé** tant que
  `status ≠ accepted` ; en V1 le `PaymentProvider` est une simulation (mock)
  substituable par Stripe sans refonte.
- **§15 Flux :** `created → pending_review → (revue) → accepted → (paiement sim)
  → assigned → exécution`. `searching` réservé au dispatch multi-intervenant.
- **§13 Notifications :** ajouter `new_request_to_review` (opérateur) et
  `request_submitted` / `request_accepted` / `request_rejected` /
  `request_needs_info` (client).

---

## SOMMAIRE
1. Vue d'ensemble & principes
2. Schéma d'architecture
3. Justification de la stack (pourquoi chaque choix)
4. Composants & services
5. Rôles & modèle d'autorisation
6. Modèle de données — toutes les tables
7. Diagramme relationnel (ERD)
8. Politiques de sécurité (RLS)
9. Surface API (PostgREST + Edge Functions + Realtime)
10. Géolocalisation temps réel (le point critique)
11. Chat temps réel
12. Paiement Stripe (capture manuelle)
13. Notifications push (Expo)
14. Stockage des images
15. Flux de données détaillés
16. Scalabilité & performance
17. Sécurité & conformité (RGPD)
18. DevOps, environnements & CI/CD
19. Roadmap technique de mise en œuvre

---

## 1. Vue d'ensemble & principes

L'application repose sur une architecture **client mobile + Backend-as-a-Service (Supabase)** complétée par des **fonctions serveur (Edge Functions)** pour toute la logique sensible (paiement, attribution, notifications, devis). Aucun serveur applicatif « maison » à maintenir au lancement : on délègue l'infrastructure (auth, base, temps réel, stockage, scaling) à Supabase, et on garde la maîtrise via PostgreSQL + RLS.

**Principes d'architecture :**
1. **Sécurité par défaut** — RLS activé sur **toutes** les tables, refus par défaut, `service_role` jamais exposé côté client.
2. **La base est la source de vérité** — la machine à états de la mission vit dans PostgreSQL ; tout réagit aux transitions (triggers, Realtime).
3. **Séparer l'éphémère du persistant** — la position GPS haute fréquence passe par **Broadcast** (éphémère), pas par des écritures DB en boucle (clé de la scalabilité).
4. **Logique sensible côté serveur** — prix, paiement, attribution : **Edge Functions** uniquement, jamais de confiance au client.
5. **Multi-intervenant & multi-rôle natif** — `client / intervenant / admin` dès le modèle.
6. **Observabilité & audit** — journal des transitions, logs Edge Functions, métriques.

---

## 2. Schéma d'architecture

```
┌───────────────────────────────────────────────────────────────┐
│                     APPLICATIONS MOBILES                       │
│        React Native + Expo (1 base de code, 2 expériences)     │
│  ┌─────────────────────┐        ┌─────────────────────────┐    │
│  │   App CLIENT        │        │  App INTERVENANT (cockpit)│   │
│  └─────────────────────┘        └─────────────────────────┘    │
│   Stripe RN SDK · Maps SDK · Expo Notifications · Realtime JS  │
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
│                     │  Supavisor (pooler)                      │
│  ┌──────────────────┴─────────────────────────────────────┐  │
│  │              EDGE FUNCTIONS (Deno, service_role)         │  │
│  │  create-payment-intent · capture-payment · refund       │  │
│  │  stripe-webhook · estimate-price · assign-mission        │  │
│  │  compose-quote · send-push · zone-check                  │  │
│  └──────────────────┬─────────────────────────────────────┘  │
│   pg_cron · pg_net · Database Webhooks · Vault (secrets)      │
└──────────┬───────────────────────┬───────────────┬───────────┘
           ▼                       ▼               ▼
   ┌──────────────┐       ┌────────────────┐  ┌──────────────┐
   │    Stripe    │       │ Expo Push (FCM/ │  │ Maps Provider│
   │ (PaymentIntent│      │  APNs)         │  │ (Google/     │
   │  Connect,    │       │                │  │  Mapbox)     │
   │  webhooks)   │       │                │  │ + Twilio OTP │
   └──────────────┘       └────────────────┘  └──────────────┘
```

---

## 3. Justification de la stack (pourquoi chaque choix)

| Technologie | Pourquoi c'est adapté à CE projet |
|---|---|
| **React Native + Expo** | Une seule base de code pour **iOS d'abord puis Android** (PRD), cycle de dev rapide, **EAS Build/Submit/Update** pour publier et pousser des correctifs **OTA** sans repasser par la review App Store. Écosystème mûr pour ce dont on a besoin : `expo-location` (géoloc + tâches en arrière-plan), `expo-notifications` (push), `@stripe/stripe-react-native` (PaymentSheet natif), cartes. Permet à un fondateur seul de livrer les **deux apps** (client + cockpit) à moindre coût. |
| **Supabase** | BaaS qui **élimine le serveur à maintenir** au lancement tout en gardant **PostgreSQL** (pas de lock-in propriétaire). Fournit en un seul produit : Auth (téléphone/Apple), base, **Realtime**, **Storage**, **Edge Functions**, **RLS**. Idéal pour un solo/petite équipe visant des milliers d'utilisateurs sans équipe infra. Open-source, migrable. |
| **PostgreSQL** | Base **relationnelle transactionnelle** : un système de missions/paiements exige des **transactions ACID**, des contraintes d'intégrité et des **machines à états fiables**. Extensible : **PostGIS** (géo), **pg_cron** (tâches planifiées), **pg_net** (webhooks sortants). La **RLS** native est le pilier de la sécurité multi-rôle. |
| **Stripe** | Standard du paiement, **PCI-DSS** géré pour nous (on ne stocke jamais de carte). La **capture manuelle** (`capture_method=manual`) correspond *exactement* à votre règle métier « empreinte à la commande, débit au montant réel du ticket » (PRD §11.4). **Stripe Connect** prêt pour reverser aux intervenants quand vous passerez en multi-intervenant. Webhooks fiables, SDK RN natif (PaymentSheet, Apple Pay). |
| **Notifications push (Expo)** | `expo-notifications` + **Expo Push Service** abstrait **APNs (iOS)** et **FCM (Android)** derrière une seule API. Déclenchées proprement par les **transitions d'état** en base (Database Webhook → Edge Function `send-push`). |
| **Géoloc temps réel (Realtime Broadcast)** | Le suivi en direct (écran-signature C-19) doit être **fluide et scalable**. On utilise **Broadcast** (pub/sub éphémère faible latence) pour les positions haute fréquence — **on n'écrit pas en base à chaque tick** (sinon la DB s'effondre à l'échelle). La base ne stocke que la **dernière position** et un **tracé échantillonné**. C'est LE choix qui rend le temps réel viable à plusieurs milliers d'utilisateurs. |
| **Chat (Realtime Postgres Changes)** | Messages **persistés** (table `messages`) + diffusion via **Postgres Changes** (les messages doivent survivre, contrairement aux positions). Indicateurs « en train d'écrire » via **Broadcast** (éphémère). RLS limite l'accès aux participants de la mission. |
| **Stockage images (Supabase Storage)** | Tickets de caisse, preuves de livraison, photos de demande, avatars. Buckets avec **politiques d'accès** par mission/utilisateur, URLs signées, intégré à l'auth. |

> **En résumé :** cette stack permet à **une personne** de construire et exploiter une application de niveau professionnel, sécurisée et scalable, **sans gérer de serveurs**, tout en gardant une base **PostgreSQL standard** qu'on pourra faire évoluer ou migrer si la croissance l'exige.

---

## 4. Composants & services

### 4.1 Supabase Auth
- **Méthodes :** OTP par téléphone (via **Twilio** ou fournisseur SMS), **Sign in with Apple** (obligatoire iOS si autres connexions sociales), e-mail (reçus).
- **JWT** émis à chaque session ; contient `sub` (= `auth.uid()`) et **claims personnalisés** (le rôle), injectés par un **Custom Access Token Hook** (voir §5).
- **Sécurité :** rotation des tokens, refresh sécurisé, verrouillage anti-bruteforce sur l'OTP.

### 4.2 PostgreSQL (+ extensions)
- Extensions activées : **postgis** (géo), **pgcrypto** (UUID/chiffrement), **pg_cron** (planifié), **pg_net** (HTTP sortant), **uuid-ossp**.
- **Triggers** : journalisation des transitions de mission, `updated_at`, déclenchement de webhooks (push).
- **Fonctions** (`SECURITY DEFINER`) pour la logique transactionnelle critique (transition d'état atomique, attribution).

### 4.3 Supabase Realtime
- **Broadcast** : positions GPS live, indicateurs de frappe.
- **Presence** : statut en ligne de l'intervenant (alimente le « disponible »).
- **Postgres Changes** : transitions de statut de mission, nouveaux messages → l'UI réagit en direct.

### 4.4 Supabase Storage
- Buckets : `mission-proofs` (tickets, preuves), `request-photos` (photos de demande libre), `avatars`.
- Accès régi par politiques (URLs signées, scoping par mission/propriétaire).

### 4.5 Edge Functions (Deno) — la logique sensible
| Fonction | Rôle | Appelée par |
|---|---|---|
| `estimate-price` | Calcule prix + ETA (distance, famille, frais, affluence) | App (avant validation) |
| `create-payment-intent` | Crée un PaymentIntent Stripe (capture manuelle) | App au paiement |
| `capture-payment` | Capture le montant **réel** à la clôture | Cockpit (clôture) |
| `refund` | Remboursement (annulation, litige) | Cockpit/Admin |
| `stripe-webhook` | Reçoit & vérifie les événements Stripe | Stripe |
| `assign-mission` | Place en file / attribue selon disponibilité & zone | Trigger / app |
| `compose-quote` | Enregistre & notifie un devis (demande libre) | Cockpit |
| `send-push` | Envoie les notifications via Expo Push | Database Webhook (sur transition) |
| `zone-check` | Vérifie qu'une adresse est dans une zone couverte (PostGIS) | App (création) |

> ⚠️ **Règle d'or :** la clé `service_role` (qui contourne la RLS) n'existe **que** dans les Edge Functions et secrets serveur. **Jamais** dans l'app mobile (qui n'utilise que la clé `anon` + le JWT utilisateur).

### 4.6 Services externes
- **Stripe** (paiement + Connect futur).
- **Expo Push** (→ APNs/FCM).
- **Fournisseur de cartes** : Google Maps ou **Mapbox** (carte, itinéraire, géocodage, reverse-geocoding, autocomplétion d'adresse).
- **Twilio** (OTP SMS + numéro masqué pour les appels/§C-23).

---

## 5. Rôles & modèle d'autorisation

### 5.1 Les trois rôles
| Rôle | Description | Accès |
|---|---|---|
| `client` | Particulier qui crée des demandes | Ses propres demandes, adresses, paiements, messages, avis |
| `operator` (intervenant) | Réalise les missions | Missions qui lui sont attribuées + la file ; ses gains, avances, justificatifs |
| `admin` | Exploitation / support / modération | Accès étendu (via back-office), gestion des zones, litiges, remboursements |

### 5.2 Implémentation du rôle (claim JWT)
On stocke le rôle dans la table `profiles`, et on l'**injecte dans le JWT** via un **Custom Access Token Hook**. Ainsi, les politiques RLS lisent le rôle directement depuis le token (`auth.jwt()`), **sans requête supplémentaire** (performant, pas de récursion RLS).

```sql
-- Type de rôle
create type user_role as enum ('client', 'operator', 'admin');

-- Hook d'accès (pseudo) : ajoute le rôle au JWT à la connexion
-- claim 'user_role' = profiles.role de l'utilisateur
```

```sql
-- Helper utilisé partout dans les politiques RLS
create or replace function auth.role_claim()
returns user_role language sql stable as $$
  select coalesce(
    (auth.jwt() ->> 'user_role')::user_role,
    'client'
  );
$$;
```

### 5.3 Niveaux d'accès
- **App mobile** → clé `anon` + JWT utilisateur → soumise à la **RLS**.
- **Edge Functions** → clé `service_role` → **contourne la RLS** pour les opérations serveur contrôlées (paiement, attribution, push).
- **Back-office admin** → rôle `admin` + RLS dédiées (ou service_role selon écran).

---

## 6. Modèle de données — toutes les tables

> Conventions : PK `uuid` (`gen_random_uuid()`), `created_at`/`updated_at timestamptz`, FK explicites, **RLS activée partout**. Les enums clarifient les états.

### 6.1 Enums (machines à états & catégories)
```sql
create type user_role        as enum ('client','operator','admin');
create type mission_family   as enum ('shopping','auto','home_service','courier','custom');
create type mission_status   as enum (
  'created','searching','assigned','accepted','preparing',
  'en_route','arrived','in_progress','completed','rated',
  'cancelled','failed','quote_pending','quote_sent','quote_refused'
);
create type payment_status   as enum (
  'requires_payment_method','requires_capture','processing',
  'succeeded','partially_captured','refunded','failed','canceled'
);
create type operator_status  as enum ('offline','available','busy','paused');
create type quote_status     as enum ('pending','sent','accepted','refused','expired');
create type cancel_actor     as enum ('client','operator','system');
```

### 6.2 Identité & comptes
```sql
-- Extension de auth.users (Supabase)
create table profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  role         user_role not null default 'client',
  first_name   text not null,
  last_name    text,
  email        text,
  phone        text,
  avatar_url   text,
  locale       text default 'fr',
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

-- Données spécifiques aux intervenants
create table operator_profiles (
  id              uuid primary key references profiles(id) on delete cascade,
  status          operator_status not null default 'offline',
  vehicle_type    text,                 -- scooter, voiture, vélo...
  vehicle_plate   text,
  rating_avg      numeric(2,1) default 5.0,
  rating_count    int default 0,
  stripe_account  text,                 -- Stripe Connect (multi-intervenant futur)
  is_verified     boolean default false,
  documents       jsonb,                -- pièces (assurance, etc.)
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- Jetons d'appareils pour le push
create table device_tokens (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references profiles(id) on delete cascade,
  expo_token  text not null,
  platform    text,                     -- ios / android
  last_seen   timestamptz default now(),
  unique (user_id, expo_token)
);
```

### 6.3 Référentiel : catégories, zones, horaires
```sql
create table service_categories (
  id          uuid primary key default gen_random_uuid(),
  family      mission_family not null,
  slug        text unique not null,     -- 'milk','diapers','pharmacy','tire'...
  label       text not null,
  icon        text,
  is_active   boolean default true,     -- activable/désactivable (arbitrages légaux PRD §11.7)
  fulfillment text default 'self',      -- 'self' (auto-réalisé) | 'partner' (mise en relation)
  legal_note  text,                     -- mention affichée (ex : "sans ordonnance uniquement")
  base_fee    numeric(10,2) default 0,  -- frais de base de la famille
  sort_order  int default 0
);

-- Zones de couverture (PostGIS) — le "masque" géographique du §4
create table coverage_zones (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  area        geography(polygon, 4326) not null,  -- polygone de couverture
  is_active   boolean default true,
  created_at  timestamptz default now()
);
create index coverage_zones_gix on coverage_zones using gist (area);

-- Heures de service (le "masque" horaire)
create table service_windows (
  id          uuid primary key default gen_random_uuid(),
  zone_id     uuid references coverage_zones(id) on delete cascade,
  weekday     int not null,             -- 0=dimanche..6=samedi
  opens_at    time not null,
  closes_at   time not null
);

-- Liste d'attente (hors zone) — capture la demande latente
create table waitlist (
  id          uuid primary key default gen_random_uuid(),
  email       text,
  phone       text,
  lat         double precision,
  lng         double precision,
  created_at  timestamptz default now()
);
```

### 6.4 Adresses
```sql
create table addresses (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references profiles(id) on delete cascade,
  label         text,                   -- 'Domicile','Bureau'
  formatted     text not null,          -- adresse lisible
  details       text,                   -- étage, digicode, instructions
  location      geography(point, 4326) not null,
  is_default    boolean default false,
  created_at    timestamptz default now()
);
create index addresses_user_idx on addresses(user_id);
create index addresses_gix on addresses using gist (location);
```

### 6.5 Cœur : missions, articles, événements
```sql
create table missions (
  id              uuid primary key default gen_random_uuid(),
  client_id       uuid not null references profiles(id) on delete restrict,
  operator_id     uuid references operator_profiles(id) on delete set null, -- null tant que non attribué
  category_id     uuid references service_categories(id),
  family          mission_family not null,
  status          mission_status not null default 'created',

  -- description
  title           text,                 -- ex "Lait × 2"
  free_text       text,                 -- demande libre
  instructions    text,

  -- localisation
  dropoff_address uuid references addresses(id),
  dropoff_point   geography(point, 4326),
  pickup_point    geography(point, 4326),   -- pour coursier

  -- tarification (snapshot au moment de la commande)
  estimated_price numeric(10,2),
  estimated_eta_min int,
  service_fee     numeric(10,2),
  advance_estimate numeric(10,2),       -- avance de frais estimée
  advance_actual  numeric(10,2),        -- montant réel (ticket)
  final_amount    numeric(10,2),        -- total débité au client
  operator_earning numeric(10,2),

  -- file d'attente / planification
  queue_position  int,
  scheduled_for   timestamptz,

  -- cycle de vie
  accepted_at     timestamptz,
  completed_at    timestamptz,
  cancelled_at    timestamptz,
  cancelled_by    cancel_actor,
  cancel_reason   text,

  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
create index missions_client_idx   on missions(client_id);
create index missions_operator_idx on missions(operator_id);
create index missions_status_idx   on missions(status);
create index missions_created_idx  on missions(created_at desc);

-- Articles d'une mission (courses)
create table mission_items (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  label       text not null,
  quantity    int default 1,
  notes       text
);
create index mission_items_mission_idx on mission_items(mission_id);

-- Journal d'audit des transitions d'état (PRD §7.4)
create table mission_events (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  from_status mission_status,
  to_status   mission_status not null,
  actor_id    uuid references profiles(id),
  actor_role  user_role,
  metadata    jsonb,
  created_at  timestamptz default now()
);
create index mission_events_mission_idx on mission_events(mission_id);
```

### 6.6 Devis (demande libre)
```sql
create table quotes (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  operator_id uuid references operator_profiles(id),
  price       numeric(10,2) not null,
  eta_min     int not null,
  note        text,
  status      quote_status not null default 'pending',
  expires_at  timestamptz,
  created_at  timestamptz default now()
);
create index quotes_mission_idx on quotes(mission_id);
```

### 6.7 Paiement
```sql
-- Moyens de paiement (références Stripe, jamais le PAN)
create table payment_methods (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references profiles(id) on delete cascade,
  stripe_pm_id    text not null,        -- pm_xxx
  brand           text,                 -- visa, mastercard...
  last4           text,
  exp_month       int,
  exp_year        int,
  is_default      boolean default false,
  created_at      timestamptz default now()
);

-- Un enregistrement de paiement par mission
create table payments (
  id                  uuid primary key default gen_random_uuid(),
  mission_id          uuid not null references missions(id) on delete restrict,
  client_id           uuid not null references profiles(id),
  stripe_pi_id        text,             -- PaymentIntent
  stripe_customer_id  text,
  amount_authorized   numeric(10,2),    -- empreinte (estimation + marge)
  amount_captured     numeric(10,2),    -- débit réel
  currency            text default 'eur',
  status              payment_status not null default 'requires_payment_method',
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);
create index payments_mission_idx on payments(mission_id);

-- Avances de frais (suivi opérateur, PRD §11.4)
create table advances (
  id            uuid primary key default gen_random_uuid(),
  mission_id    uuid not null references missions(id) on delete cascade,
  operator_id   uuid not null references operator_profiles(id),
  amount        numeric(10,2) not null,
  receipt_url   text,                   -- ticket dans Storage
  reimbursed    boolean default false,
  created_at    timestamptz default now()
);

-- Versements aux intervenants (Stripe Connect — multi-intervenant futur)
create table payouts (
  id            uuid primary key default gen_random_uuid(),
  operator_id   uuid not null references operator_profiles(id),
  amount        numeric(10,2) not null,
  period_start  date,
  period_end    date,
  status        text default 'pending',
  stripe_transfer_id text,
  created_at    timestamptz default now()
);

-- Pourboires
create table tips (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  amount      numeric(10,2) not null,
  stripe_pi_id text,
  created_at  timestamptz default now()
);

-- Codes promo (V2)
create table promo_codes (
  id          uuid primary key default gen_random_uuid(),
  code        text unique not null,
  discount_type text,                   -- percent / fixed
  value       numeric(10,2),
  max_uses    int,
  uses        int default 0,
  valid_until timestamptz,
  is_active   boolean default true
);
```

### 6.8 Suivi temps réel (position)
```sql
-- Dernière position connue de l'intervenant (1 ligne / intervenant, UPSERT)
create table operator_locations (
  operator_id uuid primary key references operator_profiles(id) on delete cascade,
  location    geography(point, 4326) not null,
  heading     numeric,
  speed       numeric,
  updated_at  timestamptz default now()
);
create index operator_locations_gix on operator_locations using gist (location);

-- Tracé échantillonné d'une mission (1 point toutes les ~10-20 s, pas chaque tick)
create table mission_tracks (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  point       geography(point, 4326) not null,
  recorded_at timestamptz default now()
);
create index mission_tracks_mission_idx on mission_tracks(mission_id, recorded_at);
```
> Le **flux haute fréquence** (1 position/seconde) ne touche **pas** ces tables : il transite par **Realtime Broadcast** (voir §10). Ces tables ne reçoivent que la **dernière position** (upsert) et un **échantillon** pour l'historique.

### 6.9 Chat
```sql
create table messages (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade,
  sender_id   uuid not null references profiles(id),
  body        text not null,
  read_at     timestamptz,
  created_at  timestamptz default now()
);
create index messages_mission_idx on messages(mission_id, created_at);
```

### 6.10 Avis & notifications
```sql
create table ratings (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid not null references missions(id) on delete cascade unique,
  client_id   uuid not null references profiles(id),
  operator_id uuid not null references operator_profiles(id),
  stars       int not null check (stars between 1 and 5),
  tags        text[],
  comment     text,
  created_at  timestamptz default now()
);

create table notifications (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references profiles(id) on delete cascade,
  type        text not null,
  title       text not null,
  body        text,
  mission_id  uuid references missions(id) on delete cascade,
  read_at     timestamptz,
  created_at  timestamptz default now()
);
create index notifications_user_idx on notifications(user_id, created_at desc);
```

---

## 7. Diagramme relationnel (ERD)

```
auth.users 1───1 profiles 1───1 operator_profiles
                   │  1             │
                   │  ├──< addresses│
                   │  ├──< device_tokens
                   │  ├──< payment_methods
                   │  └──< notifications
                   │
profiles(client) 1 ─────< missions >───── 1 operator_profiles
                              │ 1
       ┌──────────────────────┼───────────────────────────┐
       │ 1..*                 │ 1..*                       │ 1
   mission_items        mission_events                  payments
                              │                            │
   quotes >──1 missions   mission_tracks >──1 missions   advances
   messages >──1 missions  ratings 1──1 missions          tips
                                                          payouts >──1 operator_profiles

service_categories 1──< missions
coverage_zones 1──< service_windows
coverage_zones (PostGIS) ⊃ addresses.location / missions.dropoff_point
operator_locations 1──1 operator_profiles
```

**Cardinalités clés :**
- Un `client` → plusieurs `missions`.
- Une `mission` → 0..1 `operator` (null tant que non attribuée).
- Une `mission` → plusieurs `mission_items`, `mission_events`, `mission_tracks`, `messages` ; 0..1 `quote` active, 1 `payment`, 0..1 `rating`, 0..* `tips`.
- Un `operator` → 1 `operator_location` (dernière position), plusieurs `advances`/`payouts`.

---

## 8. Politiques de sécurité (RLS)

> **Toutes les tables** ont `ENABLE ROW LEVEL SECURITY` + `FORCE`. **Aucune** politique permissive par défaut → refus implicite. Voici les politiques principales (extraits représentatifs).

### 8.1 profiles
```sql
alter table profiles enable row level security;

-- Chacun lit/écrit son propre profil ; l'admin lit tout
create policy profiles_select_self on profiles for select
  using (id = auth.uid() or auth.role_claim() = 'admin');

create policy profiles_update_self on profiles for update
  using (id = auth.uid());

-- Un client peut voir le profil PUBLIC de l'intervenant de SA mission
create policy profiles_select_operator_of_mission on profiles for select
  using (
    exists (
      select 1 from missions m
      join operator_profiles op on op.id = m.operator_id
      where op.id = profiles.id and m.client_id = auth.uid()
    )
  );
```

### 8.2 missions
```sql
alter table missions enable row level security;

-- Le client voit/gère SES missions
create policy missions_client_rw on missions for all
  using (client_id = auth.uid())
  with check (client_id = auth.uid());

-- L'intervenant voit les missions qui lui sont attribuées + la file non attribuée
create policy missions_operator_select on missions for select
  using (
    auth.role_claim() = 'operator'
    and (operator_id = auth.uid() or operator_id is null)
  );

-- L'intervenant ne met à jour que SES missions (transitions de statut via fonction dédiée)
create policy missions_operator_update on missions for update
  using (auth.role_claim() = 'operator' and operator_id = auth.uid());

-- Admin : accès total
create policy missions_admin_all on missions for all
  using (auth.role_claim() = 'admin');
```

> ⚠️ **Important :** les transitions de statut critiques (attribution, capture) passent par des **fonctions `SECURITY DEFINER`** ou des **Edge Functions** (service_role), pas par un simple UPDATE client — pour garantir l'atomicité et empêcher la triche (un client ne peut pas se mettre `completed` tout seul).

### 8.3 mission_items / mission_events / mission_tracks / messages
```sql
-- Pattern : accessible si l'utilisateur est partie prenante de la mission
create policy mission_items_participant on mission_items for select
  using (
    exists (select 1 from missions m
      where m.id = mission_items.mission_id
        and (m.client_id = auth.uid() or m.operator_id = auth.uid()
             or auth.role_claim() = 'admin'))
  );
-- (idem en insert/update selon le rôle ; messages : insert réservé aux 2 participants)

create policy messages_participant_insert on messages for insert
  with check (
    sender_id = auth.uid()
    and exists (select 1 from missions m
      where m.id = mission_id
        and (m.client_id = auth.uid() or m.operator_id = auth.uid()))
  );
```

### 8.4 addresses / payment_methods / device_tokens
```sql
create policy addresses_owner on addresses for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy pm_owner on payment_methods for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy tokens_owner on device_tokens for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());
```

### 8.5 payments / advances / payouts
```sql
-- Lecture seule côté client (l'écriture vient des Edge Functions en service_role)
create policy payments_client_read on payments for select
  using (client_id = auth.uid() or auth.role_claim() = 'admin');

create policy advances_operator_read on advances for select
  using (operator_id = auth.uid() or auth.role_claim() = 'admin');
-- Aucune policy d'INSERT/UPDATE côté client → seules les Edge Functions écrivent.
```

### 8.6 Référentiel (lecture publique authentifiée)
```sql
-- Catégories actives : lisibles par tout utilisateur connecté
create policy categories_read on service_categories for select
  using (auth.uid() is not null);
-- Écriture : admin uniquement.
```

### 8.7 Storage (politiques de buckets)
```sql
-- Bucket 'mission-proofs' : lecture/écriture réservées aux parties de la mission
-- (chemin = mission_id/...), via policy sur storage.objects
create policy proofs_participant on storage.objects for select
  using (
    bucket_id = 'mission-proofs'
    and exists (
      select 1 from missions m
      where m.id::text = (storage.foldername(name))[1]
        and (m.client_id = auth.uid() or m.operator_id = auth.uid()
             or auth.role_claim() = 'admin')
    )
  );
```

---

## 9. Surface API (PostgREST + Edge Functions + Realtime)

### 9.1 API auto-générée (PostgREST, soumise à la RLS)
La majorité du CRUD passe par l'API REST/PostgREST de Supabase, **filtrée par RLS** :
- `GET /rest/v1/missions?client_id=eq.{uid}` — mes missions
- `GET /rest/v1/service_categories?is_active=eq.true` — catalogue
- `POST /rest/v1/addresses` — ajouter une adresse
- `GET /rest/v1/messages?mission_id=eq.{id}` — fil de chat
- `POST /rest/v1/ratings` — noter
- etc. (chaque table = un endpoint, sécurisé par ses policies)

### 9.2 Edge Functions (logique sensible — POST authentifié JWT)
| Endpoint | Entrée | Sortie | Effet |
|---|---|---|---|
| `POST /functions/v1/zone-check` | lat,lng | `{covered, zone_id, window}` | Vérifie zone + horaires (PostGIS) |
| `POST /functions/v1/estimate-price` | catégorie, points, items | `{price, eta_min, breakdown}` | Devis instantané |
| `POST /functions/v1/create-payment-intent` | mission_id, pm_id | `{client_secret}` | Crée PI Stripe (capture manuelle) |
| `POST /functions/v1/assign-mission` | mission_id | `{queue_position, eta}` | File/attribution |
| `POST /functions/v1/capture-payment` | mission_id, amount_réel | `{status}` | Capture le montant final |
| `POST /functions/v1/refund` | mission_id | `{status}` | Remboursement |
| `POST /functions/v1/compose-quote` | mission_id, price, eta | `{quote_id}` | Devis demande libre |
| `POST /functions/v1/stripe-webhook` | (Stripe) | 200 | MAJ `payments` selon événements |
| `POST /functions/v1/send-push` | user_id, payload | `{sent}` | Expo Push (déclenché par webhook DB) |

### 9.3 Canaux Realtime
| Canal | Type | Usage |
|---|---|---|
| `mission:{id}:location` | Broadcast | Position live de l'intervenant → client |
| `mission:{id}:status` | Postgres Changes | Transitions d'état (UI réagit) |
| `mission:{id}:chat` | Postgres Changes | Nouveaux messages |
| `mission:{id}:typing` | Broadcast | Indicateur « en train d'écrire » |
| `operator:presence` | Presence | Statut en ligne (alimente la dispo) |

---

## 10. Géolocalisation temps réel (LE point critique de scalabilité)

### 10.1 Le piège à éviter
Écrire chaque position GPS (1/seconde) dans une table et la diffuser via Postgres Changes **ne passe pas l'échelle** : à quelques centaines de missions simultanées, c'est des milliers d'INSERT/réplications par seconde → saturation de la base et de la réplication logique.

### 10.2 Le pattern retenu
```
[App Intervenant]
   │ 1 position / 1-2 s
   ▼
Realtime BROADCAST  ──►  canal "mission:{id}:location"  ──►  [App Client]
   │  (éphémère, faible latence, ne touche PAS la DB)
   │
   └─ toutes les ~10-20 s OU à chaque changement d'étape :
        UPSERT operator_locations (dernière position)
        INSERT mission_tracks (échantillon pour historique/preuve)
```
- **Live (UI fluide)** → **Broadcast** (pas de persistance par tick).
- **Dernière position** (réouverture d'app, dispatch futur) → `operator_locations` en **upsert** peu fréquent.
- **Historique / preuve de trajet** → `mission_tracks` **échantillonné**.
- **En arrière-plan** : `expo-location` + **tâche de fond** (l'intervenant garde le suivi même app en arrière-plan/écran verrouillé), avec gestion fine de la **batterie** (fréquence adaptative selon vitesse/état).

### 10.3 Calculs géo (PostGIS)
- **Zone de couverture** : `ST_Contains(zone.area, point)` → autorise/refuse la demande (`zone-check`).
- **Distance / ETA de base** : `ST_Distance` entre intervenant et destination (affiné par l'API d'itinéraire pour le routier réel).
- **Plus proche intervenant** (dispatch multi-intervenant futur) : requête `ORDER BY location <-> point LIMIT 1` avec index GIST.

---

## 11. Chat temps réel
- **Persistance** : table `messages` (les messages doivent survivre → contrairement aux positions).
- **Diffusion** : **Postgres Changes** sur `messages` filtré par `mission_id` (RLS garantit que seuls les 2 participants reçoivent).
- **Typing indicator** : **Broadcast** (`mission:{id}:typing`), éphémère.
- **Accusés** : `read_at` mis à jour à l'ouverture.
- **Modération** : filtre anti-coordonnées (protège le masque + RGPD) côté Edge Function ou trigger.
- **Push** : si l'app destinataire est en arrière-plan → Database Webhook → `send-push`.

---

## 12. Paiement Stripe (capture manuelle)

### 12.1 Pourquoi la capture manuelle colle au métier
La règle PRD §11.4 (« empreinte à la commande, débit au montant réel du ticket ») = **exactement** le modèle `capture_method: 'manual'` de Stripe : on **autorise** (réserve les fonds) à la commande, on **capture** le montant réel à la clôture.

### 12.2 Flux complet
```
1. Client valide la commande (C-16)
   → Edge Function create-payment-intent :
       amount = estimation + MARGE (couvre l'ajustement ticket)
       capture_method = manual
       customer = stripe_customer_id, payment_method = pm_xxx
   → renvoie client_secret
2. App confirme via Stripe RN SDK (PaymentSheet/Apple Pay)
   → fonds AUTORISÉS (pas débités). payments.status = requires_capture
3. Mission exécutée ; intervenant saisit le MONTANT RÉEL + ticket (OP-06)
4. Clôture (OP-07) → Edge Function capture-payment :
       capture amount_to_capture = final_amount (≤ montant autorisé)
   → débit effectif. payments.status = succeeded
5. stripe-webhook confirme l'événement → MAJ payments, génération du reçu
6. Pourboire éventuel (C-25) → PaymentIntent séparé
```

### 12.3 Cas limites gérés
- **Réel < estimé** : on capture moins que l'autorisation (Stripe le permet) → le client paie le juste prix.
- **Réel > autorisé** : on **autorise avec une marge** (ex. +20 %) pour couvrir l'écart ; au-delà, **autorisation incrémentale** (si supportée) ou **second PaymentIntent**, avec **accord explicite du client** (cohérent avec le changement de prix §11.3).
- **Annulation avant capture** : on **annule l'autorisation** (les fonds sont libérés) ; frais éventuels via capture partielle/charge dédiée selon la politique §11.5.
- **Échec/litige** : `refund` (Edge Function) + traçabilité.

### 12.4 Sécurité paiement
- **Aucune** donnée de carte ne transite par notre code (SDK Stripe + `pm_id`).
- PaymentIntents créés **uniquement côté serveur** (Edge Function), jamais montant imposé par le client.
- **Webhook signé** : vérification de la signature Stripe dans `stripe-webhook` (rejet si invalide).
- **Stripe Connect** prêt (`operator_profiles.stripe_account`) pour reverser aux intervenants en V2.

---

## 13. Notifications push (Expo)

### 13.1 Chaîne
```
Transition d'état en base (ex : status → en_route)
   → Trigger / Database Webhook (pg_net)
   → Edge Function send-push
   → Expo Push API → APNs (iOS) / FCM (Android)
   → Appareil (token dans device_tokens)
```
- **Tokens** stockés dans `device_tokens` (multi-appareils par utilisateur).
- **Contenu** : titre/corps depuis le catalogue de notifications (Spec UX Partie 3), avec **deep-link** vers l'écran concerné.
- **Règles** : regroupement, silence nocturne côté client (sauf mission active), respect des permissions.
- **Idempotence** : éviter les doublons (clé d'événement).

---

## 14. Stockage des images
- **Buckets :**
  - `request-photos` — photos de demande libre (privé, scoping client/mission).
  - `mission-proofs` — tickets de caisse, preuves de livraison (scoping participants mission).
  - `avatars` — photos de profil (lecture restreinte).
- **Accès :** politiques sur `storage.objects` (chemin préfixé par `mission_id` ou `user_id`), **URLs signées** à durée limitée.
- **Upload :** direct depuis l'app (SDK Supabase) avec compression côté client ; clé `anon` + RLS.
- **Cycle de vie :** purge des images liées à des comptes supprimés (RGPD §17).

---

## 15. Flux de données détaillés

### 15.1 Création de demande → estimation → paiement
```
App Client
  → POST zone-check (lat,lng)         [Edge: PostGIS]   → couvert ? horaires ?
  → POST estimate-price               [Edge]            → prix + ETA
  → INSERT missions (status=created)  [PostgREST+RLS]
  → POST create-payment-intent        [Edge: Stripe]    → client_secret
  → confirm PaymentIntent             [Stripe RN SDK]   → autorisé
  → UPDATE missions (status=searching)
  → POST assign-mission               [Edge]            → file/attribution
```

### 15.2 Attribution → exécution → suivi
```
assign-mission place la mission (operator_id ou file)
  → Postgres Change "status" → l'app client passe en C-18/C-19
Intervenant (cockpit) :
  → Accepte → trigger mission_events + status=accepted → push client
  → Broadcast position (canal mission:{id}:location) → carte client en direct
  → "Passer à" chaque étape → status change → push + UI client
```

### 15.3 Clôture → débit → reçu → notation
```
Intervenant saisit montant réel + ticket (Storage)
  → POST capture-payment              [Edge: Stripe]    → débit réel
  → stripe-webhook → payments=succeeded
  → status=completed → push "C'est livré"
  → reçu généré ; client note (INSERT ratings) → rating_avg recalculé (trigger)
```

### 15.4 Demande libre (devis)
```
INSERT missions (family=custom, status=quote_pending)
  → push opérateur "devis à composer"
Cockpit → POST compose-quote → INSERT quotes(status=sent) + status=quote_sent
  → push client "devis prêt"
Client accepte → create-payment-intent → flux standard
Client refuse → status=quote_refused
```

---

## 16. Scalabilité & performance (objectif : plusieurs milliers d'utilisateurs)

| Levier | Mesure concrète |
|---|---|
| **Pooling** | **Supavisor** (pooler) pour absorber les connexions des Edge Functions et de l'app. |
| **Index** | GIST sur toutes les colonnes `geography` ; index sur FK, `status`, `created_at`. |
| **Éphémère vs persistant** | Positions live en **Broadcast** (pas d'I/O DB) — le levier #1 (cf. §10). |
| **Partitionnement** | Partitionner par temps les tables à fort volume : `mission_tracks`, `messages`, `mission_events`, `notifications` (partitions mensuelles). |
| **Realtime ciblé** | N'activer Postgres Changes **que** sur les tables utiles (`missions`, `messages`), pas partout. |
| **Pagination** | Curseur (`created_at`/id) sur l'historique et le chat ; jamais de `SELECT *` non borné. |
| **Edge Functions** | Idempotentes, légères ; gérer les cold starts ; déléguer le lourd au DB ou à des jobs `pg_cron`. |
| **Read replicas** | Diriger les lectures analytiques (tableau de bord) vers des réplicas (offre Supabase) quand le volume grimpe. |
| **Cache** | Mettre en cache le référentiel quasi statique (catégories, zones) côté app. |
| **Tâches planifiées** | `pg_cron` : expiration des devis, nettoyage des tracés, recalcul d'agrégats. |
| **Mise à l'échelle Supabase** | Monter en gamme l'instance (compute) selon la charge ; surveiller via le dashboard. |
| **OTA** | `EAS Update` pour corriger sans review App Store (réactivité produit). |

---

## 17. Sécurité & conformité (RGPD)

- **RLS partout, refus par défaut** ; `service_role` cantonné aux Edge Functions.
- **Secrets** dans **Supabase Vault** / variables d'environnement (clés Stripe, Twilio) — jamais dans l'app.
- **Webhooks signés** (Stripe) ; vérification systématique.
- **Données de carte** : déléguées à Stripe (PCI-DSS) — on ne stocke que des références.
- **PII** : minimisation ; chiffrement au repos (assuré par Supabase) ; **numéro masqué** via Twilio (le client et l'intervenant ne voient jamais le vrai numéro l'un de l'autre).
- **Droits RGPD** : Edge Function `delete-account` (suppression du profil, anonymisation des missions historiques nécessaires à la comptabilité, purge Storage) ; export des données sur demande.
- **Consentement** : journalisation du consentement (CGU, géoloc, notifications).
- **Audit** : `mission_events` + logs Edge Functions = traçabilité complète.
- **Le « masque » ne touche jamais la sécurité** : le pluriel marketing (PRD §4) n'altère ni la légalité ni la protection des données.
- **Rétention** : politique de durée de conservation (positions, messages) ; purge automatisée (`pg_cron`).

---

## 18. DevOps, environnements & CI/CD

- **Environnements** : `dev` / `staging` / `prod` (3 projets Supabase distincts).
- **Migrations** : **Supabase CLI** (migrations SQL versionnées en Git) — schéma reproductible, pas de modif manuelle en prod.
- **Edge Functions** : déploiement via CLI, testées en local.
- **App mobile** : **EAS Build** (binaires iOS/Android), **EAS Submit** (App Store/Play), **EAS Update** (OTA).
- **Secrets** : gérés par environnement (jamais commités).
- **Observabilité** : logs Supabase + Edge Functions ; intégration d'un suivi d'erreurs (ex. Sentry) côté app ; métriques produit.
- **Tests** : tests des Edge Functions (paiement, attribution) ; tests RLS (un client ne doit jamais voir la mission d'un autre) — **à automatiser**, c'est la garantie de sécurité.

---

## 19. Roadmap technique de mise en œuvre

| Étape | Contenu | Dépend de |
|---|---|---|
| **T0 — Socle** | Projet Supabase, schéma de base, enums, RLS, Auth (OTP + Apple) | — |
| **T1 — Référentiel & zones** | Catégories, `coverage_zones` (PostGIS), `service_windows`, `zone-check` | T0 |
| **T2 — Cœur missions** | `missions` + machine à états + `mission_events` + triggers | T0 |
| **T3 — Tarification** | `estimate-price`, snapshots de prix | T2 |
| **T4 — Paiement** | Stripe, PI capture manuelle, webhook, `payments`/`advances` | T2, T3 |
| **T5 — Temps réel** | Broadcast position + `operator_locations` + `mission_tracks` | T2 |
| **T6 — Chat** | `messages` + Postgres Changes + push | T2 |
| **T7 — Push** | `device_tokens`, `send-push`, webhooks de transition | T2 |
| **T8 — Storage** | Buckets + policies (tickets, preuves, avatars) | T2 |
| **T9 — Avis & cockpit** | `ratings`, tableau de bord, file (`assign-mission`) | T2 |
| **T10 — Durcissement** | Tests RLS, RGPD (suppression), partitionnement, monitoring | tout |
| **T11 — Pré-prod** | Staging complet, jeux de données, EAS Build/Submit | tout |
| **V2 — Multi-intervenant** | Stripe Connect, dispatch « plus proche », `payouts`, planification | post-MVP |

---

## Décisions ouvertes (à trancher avec vous)
1. **Cartes : Google Maps ou Mapbox ?** (coût, qualité du routier en Belgique, conditions d'usage — j'ai laissé le choix ouvert ; Mapbox souvent plus souple en tarif/perso, Google plus précis sur certains POI).
2. **Fournisseur OTP/numéro masqué** : Twilio par défaut — à confirmer (alternatives : MessageBird, Vonage).
3. **Marge d'autorisation Stripe** : quel pourcentage au-dessus de l'estimation pour couvrir l'ajustement ticket (ex. +20 %) ?
4. **Suivi en arrière-plan** : confirmer le besoin de tracking background côté intervenant (impacte permissions iOS et review).
5. **Rétention des données** de position et de chat (durée légale/produit).

---

*Fin du document d'architecture technique v1.0. Les blocs SQL décrivent le schéma et les politiques de sécurité ; ils constituent la spécification de la base, pas encore le code applicatif de l'app mobile.*
