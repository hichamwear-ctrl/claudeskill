# MOBILE ARCHITECTURE — Application Expo (Client + Intervenant) — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** architecture de référence (à valider **avant** tout code écran).
> **Périmètre :** application **React Native / Expo**, **une base de code, deux expériences**
> (Client `C-*`, Intervenant/opérateur `OP-*`), sélection par **rôle** après connexion.
> L'**admin (`AD-*`) est une app web séparée** — **hors périmètre** de ce document.
> **Backend GELÉ (M1→M12)** : l'app ne fait que **consommer** les contrats existants
> (`API_SPEC.md`), sans jamais les redéfinir.
>
> **Sources de vérité :** `API_SPEC.md` (contrats), `UX_SPEC.md` (écrans/flows/erreurs),
> `Architecture_Technique.md` (stack), `DATA_MODEL.md`, `NOTIFICATIONS.md`, `CHAT.md`,
> `GPS_TRACKING.md`, `EXPO_DEMO_SETUP.md` (URL + clés + comptes de démo).

---

## 0. Principes directeurs (non négociables)

1. **Le backend est la source de vérité.** L'UI **réagit** aux transitions (Realtime), ne les
   invente pas. Aucune règle métier (prix, délais, transitions, zones, textes) **codée en dur** —
   tout vient de la base (§ référentiel/config).
2. **`anon` + JWT uniquement.** `service_role` **jamais** dans l'app (il vit dans les Edge Functions).
3. **Un seul contrat par surface.** PostgREST (lecture RLS), RPC (`SECURITY DEFINER`), Edge
   Functions (orchestration), Realtime. On n'appelle jamais deux chemins pour la même écriture.
4. **UI optimiste seulement pour l'irréversible-sûr.** Jamais pour les transitions de mission ni le
   paiement : on attend la **confirmation serveur** (UX_SPEC §1.3).
5. **4 états par écran de données** : *chargement (skeleton) · vide · erreur (réessayer) · contenu*.
6. **Feature-first + couches d'infrastructure.** Le métier vit dans `features/*` ; l'infra
   (Supabase, API, Realtime, Storage) est **mutualisée** dans `services/*`.
7. **Typé de bout en bout.** Types Postgres **générés** (`supabase gen types`) = source ; Zod pour
   la validation runtime ; aucun `any`.
8. **Évolutif sans dette.** Prêt pour Stripe réel, push réel, multi-intervenant, dark mode, Android
   — **par configuration**, sans refonte (miroir des seams backend).

---

## 1. Stack & librairies

### 1.1 À utiliser (retenu)

| Domaine | Choix | Justification |
|---|---|---|
| **Runtime** | **Expo SDK (managed)** + **EAS** (Build/Submit/Update OTA) | aligné `Architecture_Technique.md` ; OTA pour forçage de version (`min_supported`) |
| **Langage** | **TypeScript strict** | contrat typé bout-en-bout |
| **Navigation** | **expo-router** (file-based, typed routes) | groupes de routes = **rôles** (`(auth)`/`(client)`/`(operator)`), deep-links natifs |
| **Client Supabase** | **`@supabase/supabase-js`** | Auth + PostgREST + RPC + Realtime + Storage en un |
| **Cache serveur / async** | **TanStack Query (React Query)** | cache, invalidation, retry, **persistance offline**, pont Realtime→cache |
| **État client (UI/session)** | **Zustand** | léger, sans boilerplate ; session, rôle, connectivité, UI éphémère |
| **Formulaires** | **React Hook Form + Zod** | formulaire **dynamique** (moteur de questions) + validation runtime + types inférés |
| **Validation/DTO** | **Zod** | parse les réponses API, dérive les types, schémas de formulaire |
| **i18n** | **i18next + react-i18next** | 2 couches (shell bundlé + `content_strings` DB) |
| **Cartes** | **react-native-maps** (config plugin Expo) | `LiveMap`, itinéraire, position live |
| **Permissions & device** | **expo-location · expo-notifications · expo-image-picker · expo-image-manipulator · expo-secure-store · expo-haptics** | GPS, push, caméra/galerie, compression, stockage sécurisé du token, retours haptiques |
| **Connectivité** | **@react-native-community/netinfo** | `onlineManager` React Query + bannière hors-ligne |
| **Dates/argent** | **`Intl` natif + date-fns** | pas de `moment` ; formats localisés |
| **Design system** | **tokens maison + primitives** (`ui/`) | pas de lock-in ; dark-ready ; alternative future = Tamagui/Restyle |
| **Tests** | **Jest + @testing-library/react-native** (unités/hooks/UI) · **Maestro** (E2E device) | pyramide de tests |
| **Qualité** | **ESLint + Prettier + typescript-eslint** | style unifié, CI bloquante |

### 1.2 À éviter (et pourquoi)

| À éviter | Raison | À la place |
|---|---|---|
| **Redux / Redux-Toolkit** | boilerplate lourd ; le *server state* est déjà couvert | React Query + Zustand |
| **Axios** | superflu | `fetch` (Edge) + supabase-js |
| **Formik** | perfs/DX inférieures sur gros formulaires | React Hook Form |
| **moment.js** | poids/mutabilité, déprécié | `Intl` + date-fns |
| **styled-components / emotion** | coût runtime sur mobile | tokens + `StyleSheet` (ou Restyle/Tamagui) |
| **NativeBase** | lourd, maintenance en berne | design system maison |
| **WatermelonDB / Realm** | over-engineering pour l'offline V1 | persistance React Query (AsyncStorage) |
| **React Navigation « à la main »** | double emploi | expo-router (bâti dessus, typé) |
| **Stocker le JWT dans AsyncStorage** | non chiffré | **expo-secure-store** (Keychain/Keystore) |

---

## 2. Arborescence du projet

> L'app Expo vit dans **`mobile/`** à la racine du dépôt (à côté de `supabase/` et `docs/`),
> pour une séparation nette backend/mobile.

```
mobile/
├── app/                              # expo-router : ROUTES FINES (délèguent aux features)
│   ├── _layout.tsx                   # providers racine (Query, Supabase, Theme, i18n) + gate splash
│   ├── index.tsx                     # bootstrap → redirige selon session + user_role
│   ├── +not-found.tsx
│   ├── (auth)/                       # NON authentifié
│   │   ├── _layout.tsx
│   │   ├── onboarding.tsx            # C-02
│   │   ├── sign-in.tsx               # C-03  (téléphone/email OTP + Apple)
│   │   ├── verify-otp.tsx            # C-04
│   │   └── complete-profile.tsx      # C-05
│   ├── (client)/                     # garde de rôle : client
│   │   ├── _layout.tsx               # barre d'onglets + role guard
│   │   ├── (tabs)/
│   │   │   ├── home.tsx              # C-07  « De quoi avez-vous besoin ? »
│   │   │   ├── missions.tsx          # C-26  mes missions
│   │   │   ├── notifications.tsx     # C-28
│   │   │   └── profile.tsx           # C-29
│   │   ├── request/                  # pile MODALE : création de demande
│   │   │   ├── _layout.tsx
│   │   │   ├── [conversationId].tsx  # C-09/C-10 dialogue + questions dynamiques
│   │   │   └── summary.tsx           # C-13  récapitulatif → « Envoyer la demande »
│   │   └── mission/[id]/             # pile suivi/exécution
│   │       ├── index.tsx             # C-18  suivi (timeline + statut)
│   │       ├── pay.tsx               # C-17  paiement simulé (gaté « accepted »)
│   │       ├── map.tsx               # C-19  carte live
│   │       ├── chat.tsx              # C-20  chat exécution
│   │       ├── needs-info.tsx        # C-15  informations demandées (reprise conversation)
│   │       └── receipt.tsx           # C-22  clôture & reçu
│   └── (operator)/                   # garde de rôle : operator | admin
│       ├── _layout.tsx
│       ├── cockpit.tsx               # OP-03 dispo + mission active
│       ├── review/
│       │   ├── index.tsx             # OP-04 file des demandes
│       │   └── [id].tsx              # OP-05 détail + décision (claim/accept/reject/need_info)
│       └── mission/[id]/
│           ├── index.tsx             # OP-06 étapes d'exécution
│           ├── capture.tsx           # OP-07/08 montant réel + preuve → capture
│           ├── map.tsx               # OP-09 navigation
│           └── chat.tsx              # OP-10
│
├── src/
│   ├── features/                     # DOMAINE (feature-first) — chaque feature est autonome
│   │   ├── auth/                     # sign-in, OTP, Apple, session lifecycle
│   │   ├── intake/                   # conversation (converse), moteur de questions dynamiques
│   │   ├── missions/                 # mission_overview, liste, timeline, statut
│   │   ├── payments/                 # authorize/capture (Edge payments)
│   │   ├── chat/                     # messages, typing, read receipts
│   │   ├── tracking/                 # GPS live (Broadcast) + update_location
│   │   ├── review/                   # cockpit opérateur : queue + décision
│   │   ├── notifications/            # liste in-app + registration push
│   │   └── profile/                  # profil, adresses, préférences, RGPD
│   │       # convention par feature :
│   │       #   api/          appels typés (PostgREST / RPC / Edge)
│   │       #   hooks/        hooks React Query + Realtime
│   │       #   components/   composants spécifiques à la feature
│   │       #   types.ts      DTO/domaine (dérivés des types générés + Zod)
│   │       #   index.ts      barrel (surface publique de la feature)
│   │
│   ├── services/                     # INFRASTRUCTURE transverse (aucun métier)
│   │   ├── supabase/                 # client, adapter secure-store, onAuthStateChange
│   │   ├── api/                      # callEdge (enveloppe/erreurs/idempotence/version) + callRpc
│   │   ├── realtime/                 # RealtimeManager (channels privés, reconnexion, setAuth)
│   │   ├── storage/                  # uploads (compression → bucket privé) + URLs signées
│   │   ├── notifications/            # enregistrement device_token + handlers de tap
│   │   ├── config/                   # app_config + référentiel (catalogue/questions) mis en cache
│   │   └── i18n/                     # init i18next + backend content_strings
│   │
│   ├── stores/                       # Zustand : useSessionStore, useConnectivityStore, useUiStore
│   ├── ui/                           # DESIGN SYSTEM
│   │   ├── theme/                    # tokens, ThemeProvider, useTheme (light V1, dark-ready)
│   │   ├── primitives/               # Box, Text, Button, Input, Icon…
│   │   └── components/               # StatusBadge, MissionCard, PriceBreakdown, EmptyState,
│   │                                 # Skeleton, Toast/Banner, ChatBubble, LiveMap, PhotoPicker…
│   ├── hooks/                        # hooks partagés (usePermission, useDebounce, useAppState…)
│   ├── lib/                          # utils PURS (money, date, result, mission-status, cn)
│   ├── types/                        # database.types.ts (généré) + types de domaine
│   └── constants/                    # clés de query, noms de canaux, routes, error-codes
│
├── assets/                           # images, polices, icônes
├── locales/                          # fr.json (chaînes du shell) — content_strings = DB
├── app.config.ts                     # config Expo + plugins + variables EXPO_PUBLIC_*
├── eas.json                          # profils build (dev/preview/prod)
├── env.d.ts                          # typage des variables d'environnement
├── tsconfig.json                     # strict + alias @/*
├── babel.config.js · metro.config.js
└── package.json
```

**Règle d'or de séparation :** `app/*` ne contient **que** de la composition d'écran (layout + appel
de hooks de feature). Zéro `fetch`, zéro logique métier dans `app/*`.

---

## 3. Conventions

### 3.1 Nommage

| Élément | Convention | Exemple |
|---|---|---|
| Composant / primitive | `PascalCase.tsx`, export **nommé** | `MissionCard.tsx` → `export function MissionCard` |
| Hook | `useXxx.ts` | `useMissionOverview.ts` |
| Store Zustand | `useXxxStore.ts` | `useSessionStore.ts` |
| Fonction API | `verbe + objet` | `submitRequest()`, `authorizePayment()` |
| Fichier util | `camelCase.ts`, fonctions pures | `money.ts`, `missionStatus.ts` |
| Type / interface | `PascalCase` (pas de préfixe `I`) | `Mission`, `ReviewDecision` |
| Route expo-router | `kebab-case` / `[param]` | `verify-otp.tsx`, `mission/[id]/pay.tsx` |
| Clé de query | fabrique centralisée | `qk.missions.overview(id)` |
| Canal Realtime | constante centralisée | `channels.missionStatus(id)` → `mission:{id}:status` |
| Constante | `SCREAMING_SNAKE_CASE` | `MAX_PHOTO_MB` |
| Variable env exposée | `EXPO_PUBLIC_*` | `EXPO_PUBLIC_SUPABASE_URL` |

### 3.2 TypeScript

- `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`. **`any` interdit**
  (`unknown` + parse Zod aux frontières réseau).
- **Types générés = source** : `supabase gen types typescript` → `src/types/database.types.ts`.
  Les DTO de feature en **dérivent** (`type Mission = Tables<'missions'>`).
- **`mission_status`** et autres enums = **unions discriminées** issues des types générés ; aucun
  `string` libre pour un statut.
- **Résultat d'API** : les fonctions `api/` **lancent** un `AppError` typé (jamais de tuple silencieux) ;
  les hooks React Query exposent `error` typé.
- **Zod aux frontières** : toute réponse Edge/RPC est `schema.parse()` avant d'entrer dans le domaine.
- **Alias** : `@/*` → `src/*`. Barrel `index.ts` par feature = **seule surface importable**.
- Pas d'export par défaut (sauf routes expo-router qui l'exigent).

### 3.3 Style & qualité

- ESLint (typescript-eslint, react-hooks, import/order) + Prettier ; **CI bloquante** :
  `typecheck`, `lint`, `test`.
- Composants **fonctionnels** ; effets minimaux (préférer React Query/Realtime aux `useEffect`).
- Fichiers < ~200 lignes ; au-delà → découper en sous-composants/hooks.

---

## 4. Navigation & gestion des rôles

### 4.1 Modèle

- **expo-router** avec **groupes de routes** = frontières de rôle :
  `(auth)` (non connecté) · `(client)` · `(operator)` (operator **et** admin, l'admin pouvant
  observer le cockpit ; l'admin complet reste sur le web).
- **`app/index.tsx` (bootstrap)** : lit la session + le claim `user_role` → `redirect` vers
  `(auth)/sign-in`, `(client)/(tabs)/home` ou `(operator)/cockpit`.
- **Garde de rôle** dans chaque `_layout.tsx` de groupe : `useRequireRole('client')` — si le rôle ne
  correspond pas → redirection douce (jamais d'écran interdit affiché).

### 4.2 Structure de navigation par rôle (UX_SPEC §0)

- **Client** : **barre d'onglets** (Accueil · Missions · Notifications · Profil) + **piles modales**
  pour la *création de demande* (`request/*`) et le *suivi de mission* (`mission/[id]/*`).
- **Intervenant** : **cockpit à écran unique** piloté par l'état de la mission (`cockpit.tsx`) + piles
  (revue `review/*`, mission en cours `mission/[id]/*`).
- **Deep-links** : `mission/{id}` et `mission/{id}/chat` sont **adressables** (reprise sur mission
  active, tap de notification) — cf. §12.

### 4.3 Source du rôle

- Le rôle vient du **claim JWT `user_role`** (injecté par le hook `custom_access_token_hook`).
  On le lit en **décodant l'access token** (`jwt-decode`) au chargement de session ; on **ne fait
  jamais confiance** à un rôle stocké localement pour une décision de sécurité (la RLS/les RPC
  tranchent côté serveur — l'app ne fait que router l'UX).
- Après **promotion** (opérateur/admin), l'utilisateur doit se **reconnecter** pour un token à jour
  (documenté dans `EXPO_DEMO_SETUP.md`).

---

## 5. Session Supabase

- **Client unique** (`services/supabase/client.ts`) : `createClient(EXPO_PUBLIC_SUPABASE_URL,
  EXPO_PUBLIC_SUPABASE_ANON_KEY, { auth: { storage: SecureStoreAdapter, autoRefreshToken: true,
  persistSession: true, detectSessionInUrl: false } })`.
- **Stockage du token** : **expo-secure-store** (Keychain/Keystore) via un adapter
  `{ getItem, setItem, removeItem }`. Jamais AsyncStorage pour l'auth.
- **Cycle de vie** : `supabase.auth.onAuthStateChange` alimente `useSessionStore`
  (`SIGNED_IN`/`SIGNED_OUT`/`TOKEN_REFRESHED`) → recalcule `user_role`, (dé)clenche
  l'enregistrement du `device_token`, propage le token au **RealtimeManager** (`setAuth`).
- **AppState** : rafraîchissement à la reprise (`startAutoRefresh`/`stopAutoRefresh` selon
  actif/arrière-plan) pour la fiabilité du refresh.
- **Expiration** (`ERR_SESSION`) : redirection **douce** vers `(auth)` + message non alarmant
  (UX_SPEC §2), sans perdre l'intention en cours (retour au deep-link après reconnexion).

---

## 6. Structure des appels API

Quatre surfaces, un adaptateur par surface, consommées **exclusivement** via React Query.

### 6.1 Edge Functions — `services/api/edge.ts`

```
callEdge<TIn, TOut>(fn: EdgeName, body: TIn, opts?: { idempotencyKey?: string, signal?: AbortSignal }): Promise<TOut>
```

- Ajoute `Authorization: Bearer <access_token>`, `X-Api-Version: 1`, `apikey: <anon>`,
  `Idempotency-Key` (mutations sensibles : paiement, transitions à effet).
- **Déballe l'enveloppe** : succès `{ data }` → `data` ; erreur `{ error: { message, code } }` →
  **lève `AppError(code, message, httpStatus)`**.
- Gère `min_supported` (en-tête/réponse de version) → déclenche l'écran **« mise à jour requise »**
  (OTA/EAS).
- Fonctions consommées par le mobile : `converse`, `submit-request`, `review`, `estimate-price`,
  `zone-check`, `payments`, `health`. (`send-push` = **interne**, jamais appelé par l'app.)

### 6.2 RPC — `services/api/rpc.ts`

```
callRpc<TOut>(fn, args): Promise<TOut>   // supabase.rpc + mapping d'erreur homogène (SQLSTATE → AppError)
```

- RPC mobiles : `operator_queue`, `mission_overview`, `transition_mission`, `update_location`,
  `get_operator_location`, `mark_messages_read`, `estimate_price`/`zone_check` (aussi via Edge),
  `admin_stats`/`validate_config` (rôle admin, usage marginal en mobile).
- Même **catalogue d'erreurs** que l'Edge (§8) → mapping unifié `code → ERR_*`.

### 6.3 PostgREST — via supabase-js (lecture RLS)

- Lectures **soumises à la RLS** : référentiel (`service_categories`, `questions`,
  `question_options`), `addresses`, `missions` (les siennes/la file), `messages`, `notifications`,
  `app_config?scope=eq.public`.
- **Jamais** d'`UPDATE` direct de `missions.status` (interdit RLS) → toujours `transition_mission`.
- Pagination **par curseur** (`created_at`/`id`), jamais de `select('*')` non borné.

### 6.4 Organisation

- Chaque feature expose `features/<x>/api/*.ts` (fonctions pures d'accès) **consommées uniquement**
  par `features/<x>/hooks/*` (React Query). Les écrans n'appellent **que** les hooks.

---

## 7. RPC, Realtime, cache, offline

### 7.1 Gestion des RPC

- Wrappers typés (`callRpc`), erreurs mappées, invalidation React Query ciblée après mutation
  (ex. `transition_mission` → invalide `qk.missions.overview(id)` **et** attend l'écho Realtime
  `:status` pour l'UI définitive — pas d'optimisme sur les transitions).

### 7.2 Realtime — `services/realtime/`

- **RealtimeManager** : cache de channels **par topic**, (dé)abonnement lié au cycle de vie du
  composant, **reconnexion** avec backoff, `setAuth(token)` à chaque refresh de session.
- Tous les canaux `mission:{id}:*` et `operator:*` sont **privés** (Realtime Authorization
  `can_access_topic`/`can_publish_topic`). Noms **centralisés** (`constants/channels.ts`) et
  **stables** (API_SPEC §7).

| Hook | Canal | Type | Usage |
|---|---|---|---|
| `useMissionStatus(id)` | `mission:{id}:status` | Postgres Changes | maj timeline/badge → `setQueryData` |
| `useMissionChat(id)` | `mission:{id}:chat` | Postgres Changes | nouveaux `messages` |
| `useTyping(id)` | `mission:{id}:typing` | Broadcast | indicateur de frappe |
| `useOperatorLocation(id)` | `mission:{id}:location` | Broadcast | position live (client lit) |
| `usePublishLocation(id)` | `mission:{id}:location` | Broadcast | **intervenant assigné seul** publie |
| `useReviewInbox()` | `operator:review-inbox` | Postgres Changes | nouvelles demandes (opérateur) |
| `useOperatorPresence()` | `operator:presence` | Presence | disponibilité (toggle cockpit) |

- **Pont Realtime → cache** : les événements **mettent à jour le cache React Query**
  (`setQueryData`/`invalidateQueries`), jamais un état local parallèle (principe §0.1).

### 7.3 Cache — React Query

- **Paliers de fraîcheur** :
  - *Référentiel & config* (catalogue, questions, `app_config`, `content_strings`) : `staleTime`
    long + **persistance** (rechargement rare, disponible hors-ligne).
  - *Données de mission* (`mission_overview`, listes) : `staleTime` court, **invalidées par Realtime**.
  - *Temps réel pur* (position, frappe) : hors cache persistant (éphémère, Broadcast).
- **Clés centralisées** (`constants/queryKeys.ts`, fabrique `qk`) pour invalidations sûres.

### 7.4 Stratégie offline

- **Persistance** du QueryClient (AsyncStorage `persistQueryClient`) → **lecture** du référentiel et
  des dernières missions **hors-ligne**.
- **`onlineManager`** branché sur **NetInfo** + `focusManager` sur AppState → reprises/refetch
  automatiques au retour réseau/focus.
- **Bannière « Hors connexion »** persistante (UX_SPEC §2) ; **écritures désactivées** hors-ligne.
- **File d'attente** limitée aux mutations **réversibles et sûres** (ex. ajout d'adresse) — **jamais**
  paiement ni transition de mission (principe §0.4). Reprise à la reconnexion.

---

## 8. Gestion des erreurs

- **`AppError`** normalisé `{ code, message, httpStatus }`. Le `code` provient du **catalogue Edge**
  (`unauthenticated`, `forbidden`, `bad_request`, `not_found`, `conflict`, `payment_locked`,
  `zone_uncovered`, `out_of_hours`, `validation_failed`, `rate_limited`, `internal_error`).
- **Mapping unique `code → ERR_* (UX_SPEC §8)`** dans `lib/errorCatalog.ts` → message **rassurant**,
  action associée (Réessayer / Réglages / Attendre la décision / Nouvelle demande…). **Jamais** de
  code brut à l'écran.
- **Présentation** : bannière (erreur d'écran, avec **Réessayer**) ou toast (action ponctuelle) ;
  cas dédiés → écrans (`zone_uncovered`→C-08, `payment_locked`→message C-14, `ERR_SESSION`→auth).
- **Error Boundary** racine (crash inattendu) + `onError` global React Query (log corrélé
  `x-request-id`).

---

## 9. Formulaires

- **React Hook Form + Zod** partout.
- **Moteur de formulaire dynamique** (`features/intake`) : les **questions** (`type`, `options`,
  `validation`, `required_when`) → **schéma Zod construit dynamiquement** + rendu de champs typés
  (`text`/`number`/`select`/`multiselect`/`photo`/`date`…). Les **conditions de visibilité** sont
  évaluées côté client (miroir du moteur backend) **puis revalidées serveur** (`submit-request` fait
  foi ; on **n'affiche jamais** une demande « confirmée » avant décision).
- Champs contrôlés par les **primitives `ui/`** (accessibilité, états d'erreur homogènes).

---

## 10. Permissions (GPS · caméra · notifications)

- **Demande *just-in-time* avec écran d'explication** (C-06) avant l'appel système ; **jamais** au
  démarrage à froid.
- Hook central **`usePermission(kind)`** (`location` | `notifications` | `camera` | `mediaLibrary`) :
  état (`granted`/`denied`/`undetermined`), action de demande, **repli « Ouvrir les réglages »**
  (`Linking`) si refus définitif (UX_SPEC : `ERR_LOCATION_OFF`, `ERR_PERMISSION_NOTIF`).
- **GPS (`expo-location`)** : **foreground uniquement** en V1, **seulement pendant une mission
  active** (pas de tracking permanent — `GPS_TRACKING.md`). L'intervenant publie via
  `usePublishLocation` + `update_location` ; arrêt à la fin de mission.
- **Notifications (`expo-notifications`)** : permission → enregistrement `device_token` (§11).
- **Caméra/galerie (`expo-image-picker`)** : demande à l'usage (photo de demande, ticket).

---

## 11. Uploads & Storage

- **Buckets privés** (`avatars`, `request-photos`, `mission-proofs`, `documents`) — **URLs signées**
  uniquement (aucune lecture publique).
- **Pipeline** (`services/storage`) : sélection (`expo-image-picker`) → **compression**
  (`expo-image-manipulator`, borne `MAX_PHOTO_MB`) → upload `supabase.storage` vers un **chemin
  conventionnel** (`{bucket}/{userId}/{missionId}/{uuid}.jpg`) → référence stockée dans le domaine.
- **Affichage** : `createSignedUrl` (TTL court) + cache mémoire.
- **`mission-proofs`** : upload réservé aux **participants** (policy staging M12) — utilisé par
  OP-07 (ticket) ; `request-photos` par le client (C-09/C-10).
- **Robustesse** : progression, **retry** (`ERR_UPLOAD`), annulation.

---

## 12. Notifications (in-app + push)

- **In-app** : lecture `notifications` (PostgREST, RLS destinataire) → liste C-28 + **badge** ;
  `mark_*_read` ; invalidation par Realtime/refetch.
- **Push** : `expo-notifications` → obtention du token Expo → **upsert `device_tokens`** après
  connexion (et nettoyage à la déconnexion). En **démo, `push_enabled=false`** → **in-app seul**
  (aucun service externe) ; le passage au push réel est **serveur** (`DEPLOYMENT.md`), **sans code
  mobile à changer** hormis l'enregistrement du token (déjà en place).
- **Tap → deep-link** : `notifications.data.deep_link` (ex. `mission/{id}`) routé par expo-router.
- **Silence nocturne / min_interval** : gérés **côté serveur** (`dispatch_notifications`) ; l'app se
  contente d'afficher.

---

## 13. Design system, thème & i18n

### 13.1 Thème (`ui/theme`)

- **Tokens** : couleurs (sémantiques + `mission_status`), typographie (échelle + tailles
  dynamiques), espacements (grille 4/8), rayons, ombres, durées d'animation.
- **`ThemeProvider` + `useTheme`** ; **clair en V1**, **dark-ready** (tokens sémantiques, jamais de
  couleur en dur dans les composants).
- **`StatusBadge`** mappe `mission_status → {couleur + libellé}` (jamais l'information par la seule
  couleur — a11y).

### 13.2 i18n (`services/i18n`)

- **Deux couches** :
  1. **Shell de l'app** (labels de navigation, boutons, erreurs UX) : **i18next**, `locales/fr.json`
     **bundlé** (fr V1).
  2. **Contenu piloté par la donnée** (catalogue, questions, notifications, statuts) :
     **`content_strings`** chargées depuis la base (locale `profiles.locale`, défaut `fr`) et **mises
     en cache**.
- **Zéro texte métier en dur** (UX_SPEC §10). Clé manquante → repli lisible + log.

### 13.3 Composants (`ui/components` — UX_SPEC §3)

`Button` · `OtpInput` · `PhoneInput` · `CategoryCard` · `MissionCard` · `StatusBadge` ·
`MissionTimeline/Stepper` · `LiveMap` · `PriceBreakdown` · `AddressPicker` · `PhotoPicker` ·
`ChatBubble/ChatComposer` · `RatingStars` · `BottomSheet` · `ConfirmDialog` · `Toast/Banner` ·
`Skeleton` · `EmptyState` · `Avatar` · `AvailabilityToggle`.

---

## 14. Stores (Zustand) & hooks & services — récap des rôles

- **`stores/`** (état **client** uniquement, non serveur) :
  `useSessionStore` (session, `user_role`, statut de bootstrap) ·
  `useConnectivityStore` (online/offline) · `useUiStore` (toasts, bottom-sheets, thème).
- **`services/`** = infra sans métier (Supabase, api, realtime, storage, notifications, config, i18n).
- **`features/*/hooks/`** = **server state** (React Query) + Realtime, **seule** porte d'entrée des
  écrans. Règle : *écran → hook de feature → api de feature → service*.

---

## 15. Roadmap de développement (modules autonomes, testables, validables)

> Même discipline que le backend : **un module complet à la fois**, **validé avant le suivant**.
> Chaque module liste : *objectif · écrans/livrables · critères de validation*. Les modules **M0→M5**
> sont des **fondations sans écran métier** ; les écrans métier commencent en **M6**.

### MOBILE M0 — Fondations projet
- **Objectif :** squelette Expo prêt à industrialiser.
- **Livrables :** init Expo (managed) + TS strict + alias `@/*` ; expo-router ; ESLint/Prettier ;
  `app.config.ts` + variables `EXPO_PUBLIC_*` ; profils `eas.json` (dev/preview/prod) ; arborescence
  `src/*` ; CI `typecheck`+`lint`+`test`.
- **Validation :** l'app démarre (écran vide), `typecheck`/`lint`/`test` **verts**, build EAS *dev* OK.

### MOBILE M1 — Socle technique & connexion backend
- **Objectif :** parler au backend gelé, typé et sécurisé.
- **Livrables :** client Supabase (**secure-store**) ; `useSessionStore` + `onAuthStateChange` ;
  providers racine (QueryClient, Theme, i18n) ; `callEdge`/`callRpc` (enveloppe, erreurs, idempotence,
  `X-Api-Version`) ; **types générés** (`supabase gen types`) ; **appel `health`** de bout en bout.
- **Validation :** `health` renvoie `{status:"ok"}` via `callEdge` ; erreurs mappées en `AppError` ;
  session persiste au redémarrage.

### MOBILE M2 — Design System & thème
- **Objectif :** langage visuel unifié, a11y, dark-ready.
- **Livrables :** tokens + `ThemeProvider`/`useTheme` ; primitives (`Box/Text/Button/Input/Icon`) ;
  composants transverses (`StatusBadge`, `EmptyState`, `Skeleton`, `Toast/Banner`, `MissionCard`
  coquille) ; i18n `fr.json` initial ; **écran-galerie** de composants (dev only).
- **Validation :** galerie rend tous les composants ; cibles ≥ 44 px, contraste AA ; statuts =
  couleur **+** libellé.

### MOBILE M3 — Navigation & rôles
- **Objectif :** router par rôle, proprement.
- **Livrables :** groupes `(auth)`/`(client)`/`(operator)` ; `app/index.tsx` bootstrap
  (session+`user_role`) ; `useRequireRole` ; coquilles barre d'onglets (client) & cockpit (opérateur) ;
  config **deep-links**.
- **Validation :** avec sessions simulées (client/opérateur/nul), la redirection est correcte ; un
  rôle ne peut pas atteindre le groupe d'un autre.

### MOBILE M4 — Authentification & session
- **Objectif :** entrer/sortir de l'app en conditions réelles.
- **Écrans :** C-02 onboarding · C-03 sign-in (**OTP téléphone/email + Apple**) · C-04 verify-otp ·
  C-05 complete-profile.
- **Livrables :** cycle de vie session (refresh, `ERR_SESSION` → redirection douce) ; **enregistrement
  `device_token`** post-login ; déconnexion (purge secure-store + token) ; lecture `user_role` (décodage JWT).
- **Validation :** login **email OTP** de bout en bout (compte démo `EXPO_DEMO_SETUP.md`) ; le JWT
  contient `user_role` ; routes protégées ; logout propre.

### MOBILE M5 — Référentiel & configuration
- **Objectif :** app **data-driven**, disponible hors-ligne.
- **Livrables :** chargement `app_config?scope=eq.public` + catalogue + **schéma des questions** ;
  cache **persistant** (React Query) ; loader `content_strings` (i18n couche 2) ; **feature flags**
  (`feature.*`).
- **Validation :** config/référentiel lus **hors-ligne** ; aucun texte métier en dur ; flags respectés.

### MOBILE M6 — Intake conversationnel (Client)
- **Objectif :** créer une demande jusqu'à `pending_review`.
- **Écrans :** C-07 accueil (saisie libre) · C-09/C-10 dialogue + **formulaire dynamique** · C-13
  récapitulatif → **« Envoyer la demande »**.
- **Livrables :** boucle `converse` ; **moteur de questions** (RHF+Zod, conditions) ; `zone-check` +
  `estimate-price` (états `ERR_ZONE_UNCOVERED`/`ERR_OUT_OF_HOURS` → C-08) ; `submit-request`.
- **Validation :** un parcours réel crée **une mission `pending_review`** (staging mock) ; revalidation
  serveur des requis ; jamais de « confirmé » avant décision.

### MOBILE M7 — Suivi de mission (Client)
- **Objectif :** refléter en **temps réel** la vie de la mission.
- **Écrans :** C-26 mes missions · C-18 suivi (timeline/`StatusBadge`) · C-14 en attente · C-15
  needs_information (reprise conversation) · C-16 refusée · C-19 carte live.
- **Livrables :** `mission_overview` (1 appel consolidé) ; `useMissionStatus` (Realtime→cache) ;
  `useOperatorLocation` (Broadcast) + `LiveMap` (repli dernière position).
- **Validation :** une transition serveur se reflète **sans refresh manuel** ; la carte suit la
  position live puis retombe sur le repli.

### MOBILE M8 — Paiement simulé (Client)
- **Objectif :** le **gate P1** côté UX.
- **Écrans :** C-17 paiement (**visible seulement après `accepted`**) · C-22 clôture & reçu.
- **Livrables :** Edge `payments` (`authorize`, mock) avec **`Idempotency-Key`** ; affichage
  `PriceBreakdown`/devis `custom` ; capture/reçu (lecture) ; `ERR_PAY_LOCKED`/`ERR_PRICE_EXPIRED`.
- **Validation :** `authorize` → mission `assigned` ; toute tentative avant acceptation est **bloquée**
  (UI + serveur) ; idempotence (double tap = un seul paiement).

### MOBILE M9 — Chat d'exécution (Client + Intervenant)
- **Objectif :** messagerie **d'exécution** (≠ intake), temps réel.
- **Écrans :** C-20 / OP-10.
- **Livrables :** liste `messages` (Postgres Changes) ; composer = **INSERT** (RLS) ; `useTyping`
  (Broadcast) ; `mark_messages_read` (badges non-lus) ; upload photo (`request-photos`) ; gestion du
  refus de **modération** (déterministe).
- **Validation :** échange bilatéral **temps réel** ; compteurs non-lus corrects ; message modéré →
  message d'erreur clair.

### MOBILE M10 — Cockpit intervenant
- **Objectif :** revue + exécution complètes côté opérateur.
- **Écrans :** OP-03 cockpit (dispo **Presence**) · OP-04 file (`operator:review-inbox`) · OP-05
  décision · OP-06 étapes · OP-07/08 montant+preuve → capture.
- **Livrables :** `operator_queue` + `review` (claim/accept/reject/need_info) ; `transition_mission`
  (étapes, confirmation serveur) ; upload `mission-proofs` ; **GPS émission** (`update_location` +
  `usePublishLocation`, mission active seulement) ; `payments` (`capture`, mock).
- **Validation :** parcours opérateur complet (claim→décision→exécution→capture→`completed`) ; un
  non-claimeur ne peut pas décider ; position publiée **uniquement** par l'assigné.

### MOBILE M11 — Notifications & permissions
- **Objectif :** notifications robustes + permissions propres.
- **Écrans :** C-06 permissions · C-28 notifications (in-app).
- **Livrables :** `usePermission` (location/notifications/camera) + replis réglages ; liste in-app +
  badges ; **deep-link** au tap ; enregistrement/cycle `device_token` finalisé.
- **Validation :** permissions demandées *just-in-time* ; tap de notification → bon écran ; en démo,
  in-app seul (aucun service externe).

### MOBILE M12 — Offline, résilience, erreurs & QA E2E
- **Objectif :** finition « pro » et validation de bout en bout.
- **Livrables :** persistance React Query ; `onlineManager`/`focusManager` (NetInfo/AppState) ;
  **bannière hors-ligne** + écritures verrouillées ; file de mutations sûres ; **Error Boundary** +
  `onError` global ; **audit des 4 états** sur chaque écran de données ; parcours **E2E Maestro**
  (client + opérateur) contre le **staging mock**.
- **Validation :** lecture hors-ligne OK ; erreurs toujours rassurantes/actionnables ; **E2E vert**
  (soumission → revue → paiement → exécution → chat → GPS → clôture → notifs in-app).

---

## 16. Alignement backend ↔ mobile (traçabilité)

| Besoin mobile | Contrat backend (gelé) |
|---|---|
| Auth + rôle | Supabase Auth (OTP/Apple/email) + claim `user_role` (hook) |
| Créer une demande | Edge `converse` → `submit-request` (mission `pending_review`) |
| Zone/prix | Edge `zone-check` / `estimate-price` (RPC PostGIS) |
| Suivi consolidé | RPC `mission_overview` |
| Statut live | Realtime `mission:{id}:status` (Postgres Changes) |
| Paiement (gate P1) | Edge `payments` (`authorize`/`capture`, mock, `Idempotency-Key`) |
| Chat exécution | `messages` (INSERT+Changes) · `mark_messages_read` · `:typing` (Broadcast) |
| GPS live | `update_location` / `get_operator_location` · `:location` (Broadcast) |
| Cockpit opérateur | RPC `operator_queue` · Edge `review` · RPC `transition_mission` |
| Notifications | `notifications` (RLS) + `device_tokens` (push serveur, `push_enabled`) |
| Contenus/i18n | `content_strings` · `app_config` · catalogue/`questions` (data-driven) |
| Uploads | Storage buckets **privés** + URLs signées (`request-photos`/`mission-proofs`) |

> **Aucune nouvelle surface d'API n'est requise.** L'app consomme les contrats existants ; toute
> évolution métier reste **côté donnée** (catalogue/questions/config) — cf. `API_SPEC.md §10`.

---

## 17. Prochaine étape

Valider cette architecture (stack, arborescence, découpage M0→M12). À l'accord, démarrer **MOBILE M0**
(fondations, **sans écran métier**), puis progresser **module par module** avec un rapport de
validation par module — même rigueur que le backend.
