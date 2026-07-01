# API SPEC — Contrats d'API — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Fil conducteur (P0) :** l'app est un **moteur de traitement de demandes**.
> L'API reflète : *besoin libre → classification (données) → questions dynamiques
> (données) → récapitulatif → `pending_review` → décision humaine → paiement
> simulé gaté → exécution suivie*. **Rien codé en dur** : catalogue, questions,
> transitions, notifications, textes, tarifs, seuils viennent de la base.
>
> **Cohérence :** `PRD.md`, `BUSINESS_RULES.md`, `SPEC_FONCTIONNELLE_V1.md`,
> `DATA_MODEL.md`, `UX_SPEC.md`, `Architecture_Technique.md`.

---

## 1. Surfaces d'API

| Surface | Usage | Sécurité |
|---|---|---|
| **PostgREST** (`/rest/v1/…`) | CRUD **soumis à la RLS** : lecture référentiel/questions, adresses, missions du client, messages, notifications, avis | clé `anon` + **JWT** utilisateur → RLS |
| **RPC** (`/rest/v1/rpc/<fn>`) | Fonctions Postgres `SECURITY DEFINER` (ex. `transition_mission`) | JWT ; garde‑fous internes (allow‑list, rôle) |
| **Edge Functions** (`/functions/v1/<fn>`) | Logique sensible/orchestration : classification, estimation, **paiement**, revue, push | JWT (sauf sondes/webhooks signés) ; `service_role` **serveur uniquement** |
| **Realtime** | Statuts, positions (Broadcast), chat (Postgres Changes), présence | JWT ; RLS sur les tables sources |

**Règle d'or :** `service_role` (contourne la RLS) **uniquement** dans les Edge
Functions. L'app mobile n'utilise que `anon` + JWT.

## 2. Conventions

- **Réponses** (Edge Functions) : succès `{"data": …}` ; erreur
  `{"error": {"message": string, "code"?: string}}`. En‑têtes CORS systématiques.
- **Codes d'erreur** stables (`HttpError.code`) mappés au catalogue UX (`ERR_*`,
  `UX_SPEC` §8). Ex. `unauthenticated`(401), `forbidden`(403), `bad_request`(400),
  `not_found`(404), `conflict`(409), `payment_locked`(409), `zone_uncovered`(422),
  `out_of_hours`(422), `validation_failed`(422), `rate_limited`(429),
  `internal_error`(500).
- **Idempotence** : en‑tête `Idempotency-Key` sur les mutations sensibles
  (paiement, transitions déclenchant des effets) ; clé d'événement pour les push.
- **Pagination** : curseur (`created_at`/`id`) ; jamais de `SELECT *` non borné.
- **i18n** : les textes renvoyés proviennent de `content_strings` (locale du
  profil) ; l'API renvoie des **clés** + valeurs résolues.
- **Corrélation** : `x-request-id` propagé et journalisé (`_shared/handler.ts`).
- **Rôles** (claim JWT `user_role`) : `client` / `operator` / `admin`.

### 2.1 Versionnement de l'API (stratégie)
- **Contrats Edge Functions** : versionnés par **en‑tête** `X-Api-Version: 1`
  (défaut `1`). Un changement **cassant** = nouvelle version servie **en
  parallèle** (l'ancienne reste jusqu'à dépréciation) ; réponses non cassantes =
  ajouts de champs seulement (jamais de retrait/renommage dans une version).
- **Compat mobile** : l'app envoie sa version ; le serveur peut renvoyer
  `min_supported` → **forçage de mise à jour** (OTA/EAS). Politique de
  **dépréciation** documentée (fenêtre de support).
- **PostgREST** : évolutions **additives** ; les changements de forme passent par
  des **vues versionnées** si nécessaire.
- **Realtime** : les **noms de canaux** (`mission:{id}:*`) sont **stables** ; un
  changement de payload = nouveau suffixe de canal.
- **RPC** : signatures stables ; nouvelle signature = nouveau nom de fonction.
- **Migrations** : additives et réversibles ; jamais de suppression de colonne en
  usage sans période de transition (compat descendante).

---

## 3. Parcours ↔ API (vue d'ensemble)

```
C-07  POST /functions/v1/classify-request      (texte libre → intentions candidates)
C-07→ POST /functions/v1/converse              (boucle dialogue : extraction + prochaine question)
      GET  /rest/v1/questions?set_id=eq.{…}     (schéma des slots ; conditions revalidées serveur)
C-13  POST /functions/v1/zone-check             (couverture + horaires)
      POST /functions/v1/estimate-price         (prix + ETA, si applicable)
      POST /functions/v1/submit-request         (created → pending_review)  → push OPÉRATEUR
OP-05 POST /functions/v1/review-request         (accept | reject | needs_information ; prix si custom)
C-17  POST /functions/v1/create-authorization   (paiement sim ; GATED status=accepted)
      (auto) assign-mission                      (accepted → assigned)
OP-06 POST /rest/v1/rpc/transition_mission       (étapes d'exécution)
OP-07 POST /functions/v1/capture-payment         (in_progress → completed)
      POST /functions/v1/refund                  (annulation/échec/litige ; admin)
```

---

## 4. Edge Functions — contrats

> Format par fonction : **méthode/chemin · auth · entrée · sortie · erreurs ·
> effets · règles**.

### 4.1 `classify-request` — besoin libre → **capacités** (P7)
- `POST /functions/v1/classify-request` · **client**
- **Entrée :** `{ text: string, locale?, media?: [storage_path], context? }`
- **Sortie :** `{ capabilities: [{ slug, score }], derived_category_id?: uuid|null,
  needs_disambiguation: bool }`
- **Erreurs :** `bad_request`, `rate_limited`.
- **Effets :** aucune écriture définitive ; peut créer/mettre à jour un
  **brouillon** (`missions.status='created'`, `metadata.classification`).
- **Règles (P7/P8) :** IA + `capability_classification` → **capacités** ; la
  catégorie interne est **dérivée** via `category_capabilities` (pour tarif/
  workflow/stats) ou `null` si aucune. Confiance faible → **capacités partielles +
  questions génériques** (jamais bloquant). **Jamais** décisif — l'opérateur
  tranche (P1).

### 4.1b `converse` — tour de dialogue (cœur conversationnel)
- `POST /functions/v1/converse` · **client (propriétaire)**
- **Entrée :** `{ conversation_id?, text?, media?, answer? }` (ouvre une
  conversation si absente).
- **Sortie :** `{ conversation_id, assistant_message, next_question?,
  filled_slots, plan?, needs_disambiguation?, ready_for_summary: bool }`
- **Erreurs :** `bad_request`, `rate_limited`, `validation_failed`.
- **Effets :** oriente le **moteur déterministe** (prochaine question à partir des
  `questions`/conditions) ; l'IA extrait les valeurs (revalidées) et reformule ;
  écrit `conversation_turns` + met à jour `conversations.state`/`plan` ; **aucune**
  création de mission définitive (reste `created`).
- **Règles :** `CONVERSATION_ENGINE.md` (BR‑CE‑*) ; P0/P1 ; l'IA **ne décide
  jamais** — s'arrête à la préparation du récapitulatif.
- **🔧 Implémentation V1 (M3) :**
  - **Entrée :** `{ conversation_id?, message?, answer?: {key,value}, locale? }`.
  - **Sortie :** `{ conversation_id, classification, next, can_summarize, invalid,
    summary }` — `next` = question présentée `{ key, type, label, help?, required,
    options }`.
  - **Classification** = classifieur **mots‑clés déterministe**
    (`app_config.classification.keywords`, éditable — P0), adaptateur **IA
    remplaçable** ; `classify-request` (§4.1) **fondu dans `converse`** en V1.
  - **Extraction** : le client **répond à la question posée** (`answer`) ; le
    message libre sert à la (re)classification. L'extraction multi‑slots par IA
    est un **ajout additif** ultérieur (le moteur reste inchangé).
  - Écrit `conversation_turns` + `conversations.state = {answers, classification}` ;
    écriture **service_role**, **propriété vérifiée en code**.

### 4.2 `zone-check` — couverture & horaires
- `POST /functions/v1/zone-check` · **client**
- **Entrée :** `{ lat, lng, at? }`
- **Sortie :** `{ covered: bool, zone_id?, open: bool, next_window? }`
- **Erreurs :** `bad_request`.
- **Effets :** aucun (sinon proposer `waitlist`).
- **Règles :** `ST_Covers` (PostGIS) + `service_windows` ; BR‑011/012/022.
- **🔧 V1 (M4) :** wrapper fin sur la RPC `zone_check(p_lng, p_lat, p_at)`
  (SECURITY DEFINER, PostGIS). Fenêtres évaluées en **heure locale**
  (`Europe/Brussels`, mono‑ville V1) ; `next_window` = prochaine ouverture.

### 4.3 `estimate-price` — prix & ETA
- `POST /functions/v1/estimate-price` · **client**
- **Entrée :** `{ category_id, dropoff_point, pickup_point?, details?, advance_estimate? }`
- **Sortie :** `{ price?, eta_min, breakdown, currency }` (pour `custom` : `price=null`)
- **Effets :** aucun (snapshot posé à la soumission).
- **Règles :** `pricing_rules` + `pricing_modifiers` (§3 SPEC) ; BR‑070/211.
- **🔧 V1 (M4) :** wrapper fin sur la RPC `estimate_price(p_category_id,
  p_dropoff_lng/lat, p_pickup_lng/lat?)`. Zone via `ST_Covers` → `pricing_rules`
  (zone sinon défaut) ; `price = max(minimum_price, base_fare + km·price_per_km)
  + category.base_fee` ; `eta = ceil(km/avg_speed·60) + prep_buffer_min`.
  Catégorie **`metadata.quote_only`** → `price=null`. **`pricing_modifiers`
  différé** (aucun supplément V1 — LEAN_V1 §1.2).

### 4.4 `submit-request` — soumission (created → pending_review)
- `POST /functions/v1/submit-request` · **client (propriétaire)**
- **Entrée :** `{ conversation_id, confirm_plan?: bool }` (le `plan` validé de la
  conversation porte la/les mission(s), détails, adresses, ordre).
- **Sortie :** `{ group_id?, missions: [{ mission_id, status: "pending_review" }], summary }`
- **Erreurs :** `validation_failed` (slots obligatoires non satisfaits),
  `zone_uncovered`, `out_of_hours`, `forbidden`.
- **Effets :** **validation serveur** des réponses (`questions.validation`,
  `required_when`) ; snapshot prix/ETA ; **crée 1..N missions** (multi‑services :
  même `group_id`, `sequence`/`depends_on` — `CONVERSATION_ENGINE.md` §7) ;
  `transition_mission(created→pending_review)` par mission ; `submitted_at` ;
  `conversations.status='submitted'` ; **notification opérateur**
  `new_request_to_review`.
- **Règles :** P1 (le client ne va pas au‑delà de `pending_review`) ; PRD‑F04/F05/F06 ;
  BR‑CE‑30→33 (découpage validé ensuite par l'opérateur).
- **🔧 Implémentation V1 (M3→M4) :**
  - **Entrée :** `{ conversation_id }`. **Sortie :** le **dossier**
    `{ conversation_id, classification, entries: [{ key, label, value, type }],
    mission_id }`.
  - **Effets V1 :** revalidation serveur (tout le requis satisfait, sinon `422
    incomplete`) ; **création atomique** (RPC `create_mission_from_conversation`,
    SECURITY DEFINER) d'**une mission `pending_review`** (`details`=réponses,
    `category_id` dérivée de la classification, `conversation_id` lié, audit
    `mission_events`) ; `conversations.status='submitted'` ; tour système
    `submitted`. **Aucun paiement, aucune décision** — la mission attend la revue
    opérateur (P1). Multi‑services (`group_id`) **différé** (1 mission/conversation
    en V1).
  - **Notification opérateur** (`send-push`) : **différée** (module notifications).
  - **Erreurs V1 :** `conversation_not_found` (404), `conversation_closed` (409),
    `incomplete` (422).

### 4.4b `review-claim` — prise en charge d'une demande (OP/ADMIN)
- `POST /functions/v1/review-claim` · **operator | admin**
- **Entrée :** `{ mission_id, release?: bool }`
- **Sortie :** `{ mission_id, claimed_by, claimed_at }`
- **Effets :** pose **atomiquement** `review_claimed_by = auth.uid()`,
  `review_claimed_at = now()` **si** non déjà claimé (verrou anti‑double‑traitement) ;
  `release=true` libère. Expiration auto après `app_config.review.claim_ttl_min`.
- **Erreurs :** `conflict` (déjà claimé par un autre), `forbidden`.
- **Effets vie privée :** tant qu'une demande n'est pas claimée, la file n'expose
  qu'un **résumé minimal** ; le **détail complet** (texte libre, transcript) n'est
  lisible qu'après claim (RLS). *(Correctif de sécurité/scalabilité.)*
- **Règles :** requis dès le multi‑opérateur ; `review-request` exige que
  l'appelant ait **claimé** la demande (ou soit admin).

### 4.5 `review-request` — décision humaine (OP/ADMIN)
- `POST /functions/v1/review-request` · **operator | admin**
- **Entrée :** `{ mission_id, decision: "accept"|"reject"|"need_info",
  price?, eta_min?, reason?, questions? }`
  - `accept` : pour `custom`, `price`+`eta_min` requis → écrit `quotes`
    (`expires_at = now + app_config.quote_validity_hours`).
  - `reject`/`need_info` : `reason` requis.
- **Sortie :** `{ mission_id, status }`
- **Erreurs :** `forbidden` (rôle **ou non‑claimeur** — cf. `review-claim`),
  `conflict` (état ≠ `pending_review`), `validation_failed` (prix manquant custom).
- **Effets :** `transition_mission` vers `accepted|rejected|needs_information` ;
  `reviewed_at`, `reviewed_by`, `review_reason` ; notif client
  (`request_accepted|request_rejected|request_needs_info`) ; si `accept` →
  **débloque le paiement**.
- **Règles :** P1 ; BR‑010→035 (critères) ; §2 BUSINESS_RULES.
- **🔧 V1 (M4) — `review` unique (absorbe claim + décision, LEAN_V1) :**
  `POST /functions/v1/review` · **operator | admin** ·
  `{ mission_id, action: 'claim'|'release'|'accept'|'reject'|'need_info',
  reason?, price?, eta_min? }`. Appelée **avec le JWT opérateur** : les RPC
  `claim_review` / `transition_mission` (SECURITY DEFINER) appliquent
  rôle + **claim actif** + allow‑list côté base. `accept` d'une catégorie
  `quote_only` exige `price` ; `reject`/`need_info` exigent `reason`. Erreurs
  mappées depuis le SQLSTATE (403 rôle/claim, 409 conflit/transition, 422 champ
  requis).

### 4.6 `create-authorization` — paiement simulé (GATED)
- `POST /functions/v1/create-authorization` · **client (propriétaire)**
- **Entrée :** `{ mission_id, payment_method_ref? }`
- **Sortie :** `{ payment_id, status: "requires_capture", amount_authorized }`
- **Erreurs :** **`payment_locked`(409) si `status ≠ accepted`** ou appelant ≠
  client ; `conflict` (déjà autorisé) ; `price_expired` (custom > 24 h).
- **Effets :** `PaymentProvider.authorize` (mock) → `payments` ; **déclenche**
  `assign-mission` (accepted → assigned).
- **Règles :** **garde‑fou fondamental** — aucun paiement avant acceptation
  (P1, BR‑210/211) ; interface remplaçable par Stripe sans changer ce contrat.
- **🔧 V1 (M5) — Edge unique `payments`** (`action: authorize|capture|void|refund`,
  absorbe §4.6/§4.7/§4.8). Orchestration **intent → PSP → settle** :
  1. `payment_intent` (JWT appelant) applique le **gate P1 en base** (statut
     `accepted`, propriété client, prix validé, idempotence 1/mission) et calcule
     `amount = prix × (1+marge%) + advance_estimate` ;
  2. `PaymentProvider` (mock ; `PAYMENT_PROVIDER=mock|stripe`) ;
  3. `payment_settle` (service_role) enregistre + **affecte la mission**
     (`accepted→assigned`, `assign_mission`). Erreurs mappées SQLSTATE
     (`payment_locked`/`price_expired`→409, propriété→403, prix manquant→422,
     déjà initié→409). **Aucun garde‑fou dans l'Edge** (tout en SQL).

### 4.7 `capture-payment` — clôture
- `POST /functions/v1/capture-payment` · **operator (assigné) | admin**
- **Entrée :** `{ mission_id, amount_final, advance_actual?, proof_path }`
- **Sortie :** `{ payment_id, status: "succeeded"|"partially_captured", final_amount }`
- **Erreurs :** `validation_failed` (preuve/ticket manquant ; montant > autorisé
  au‑delà de `price_tolerance_pct` sans accord — BR‑072), `forbidden`, `conflict`.
- **Effets :** `PaymentProvider.capture` ≤ autorisé ; `advances` (ticket) ;
  `transition_mission(in_progress→completed)` ; notif `mission_completed` +
  `receipt_available`.
- **Règles :** BR‑140→145, BR‑190→192 ; capture ≤ autorisation.
- **🔧 V1 (M5) :** via `payments` (`action:'capture'`). `payment_settle`
  **revérifie en base** `amount_captured ≤ amount_authorized` (BR‑212) et la
  **preuve** (`proof_path`, BR‑190) ; `partially_captured` si < autorisé, sinon
  `succeeded` ; pose `missions.final_amount`/`advance_actual` et transite
  `in_progress→completed` (atomique). Notification différée (module notifications).

### 4.8 `refund` — remboursement / annulation (sim)
- `POST /functions/v1/refund` · **operator (limité) | admin**
- **Entrée :** `{ mission_id, kind: "void"|"refund", amount?, reason }`
- **Sortie :** `{ payment_id, status: "canceled"|"refunded", amount }`
- **Effets :** `void` (non capturé) ou `refund` (après capture) ; notif
  `refund_simulated` ; idempotent.
- **Règles :** BR‑130→133 ; remboursement **exceptionnel** = `admin`.

### 4.9 `send-push` — notifications (interne)
- `POST /functions/v1/send-push` · **service_role** (déclenché par Database Webhook)
- **Entrée :** `{ event_key, mission_id?, user_id?, payload? }`
- **Effets :** résout `notification_triggers` → `notification_templates` →
  `content_strings` (locale) ; écrit `notifications` ; envoie Expo Push
  (`device_tokens`) ; **idempotence** par clé d'événement.
- **Règles :** `NOTIFICATIONS.md`, SPEC §6. **Data‑driven** (aucun texte en dur).

### 4.10 `assign-mission` — affectation (interne/auto)
- Déclenchée après autorisation (V1 **auto**, mono‑intervenant).
- **Effets :** `operator_id` posé ; `transition_mission(accepted→assigned)` ;
  notif `mission_new` (intervenant). En multi‑op (V2) : dispatch « plus proche ».
- **Règles :** BR‑040→045 ; PRD‑F12.
- **🔧 V1 (M5) :** **pas une Edge Function ni un trigger** — RPC `assign_mission`
  **appelée dans `payment_settle`** (atomique avec l'autorisation). `operator_id =
  reviewed_by` (mono‑opérateur V1) ; dispatch « plus proche » → V2.

---

## 5. RPC — transitions d'état

### `rpc/transition_mission`
- `POST /rest/v1/rpc/transition_mission` · **rôle selon la transition**
- **Entrée :** `{ mission_id, to_status, metadata? }`
- **Sortie :** `{ mission_id, from_status, to_status }`
- **Erreurs :** `forbidden` (rôle non autorisé pour `(from,to)`), `conflict`
  (transition non permise), `not_found`.
- **Effets :** valide contre **`mission_transitions`** (données) + rôle ; met à
  jour `missions.status` ; insère `mission_events` (acteur, motif) ; les
  **effets métier** (paiement, notifs) sont branchés par webhooks/fonctions.
- **Usage :** étapes d'exécution (OP‑06) : `assigned→shopping→…→completed`. Les
  transitions de **revue** et de **paiement** passent par leurs Edge Functions
  dédiées (§4.5/§4.6) pour l'atomicité (prix, autorisation).
- **Règles :** SPEC §2.7 ; P1 (allow‑list, rôles).
- **🔧 V1 (M4) :** signature `transition_mission(p_mission_id, p_to, p_reason?,
  p_price?, p_eta_min?, p_metadata?)` (SECURITY DEFINER, **unique écrivain du
  statut**). La table **`mission_transitions` est différée** (LEAN_V1 §1.2) :
  l'allow‑list `(from,to)→rôles` vit **en code** dans la fonction ; les **étapes
  optionnelles** (`shopping`/`preparing`) sont gatées par **`category_workflow`**
  (donnée). Écrit les colonnes dérivées (`reviewed_*`, `accepted_at`, `quoted_*`,
  `completed_at`, `cancelled_*`) + `mission_events`. Revue : exige un **claim
  actif** ; exécution : exige l'**opérateur affecté**.

---

## 6. PostgREST — surface REST (soumise à la RLS)

| Ressource | Accès | Notes |
|---|---|---|
| `GET service_categories?is_active=eq.true` | authentifié | taxonomie (usage interne/classif.), pas un menu |
| `GET conversations`, `GET conversation_turns` | propriétaire (client) ; operator/admin en revue | historique du dialogue ; écriture via `converse` |
| `GET question_sets`, `GET questions`, `GET question_options` | authentifié | **schéma des slots** ; conditions évaluées client + revalidées serveur |
| `GET/POST addresses` | propriétaire | carnet d'adresses |
| `GET missions?client_id=eq.{uid}` | client (RLS) | ses missions ; `operator` voit **les siennes + la file de revue non‑claimée + ce qu'il a claimé** (jamais le `pending_review` claimé par un autre) ; admin tout |
| `GET mission_items`, `GET mission_events` | participants | détail & timeline |
| `GET/POST messages?mission_id=eq.{id}` | participants | chat (insert réservé aux 2) |
| `GET notifications?user_id=eq.{uid}` | destinataire | liste in‑app |
| `POST ratings` | client (mission terminée) | avis facultatif |
| `GET app_config?scope=eq.public` | authentifié | seuils publics + `feature.*` |
| `POST waitlist` | authentifié | self‑insert |
| **Écriture** catalogue/tarifs/zones/questions/templates/config | **admin** | administrabilité totale (RLS admin) |

> Les **statuts de mission** ne sont **jamais** modifiés par `UPDATE` direct
> (RLS) : uniquement via `transition_mission`/Edge Functions.

---

## 7. Realtime — canaux

| Canal | Type | Émis vers | Source |
|---|---|---|---|
| `mission:{id}:status` | Postgres Changes | client + intervenant | `missions.status` |
| `mission:{id}:location` | **Broadcast** | client | position live intervenant (éphémère) |
| `mission:{id}:chat` | Postgres Changes | participants | `messages` |
| `mission:{id}:typing` | Broadcast | participants | indicateur de frappe |
| `operator:review-inbox` | Postgres Changes | opérateurs | nouvelles `missions` en `pending_review` |
| `operator:presence` | Presence | dispatch | disponibilité intervenants |

- Positions **haute fréquence** via **Broadcast** (pas d'écriture DB/tick) ;
  `operator_locations` (dernière position) et `mission_tracks` (échantillon)
  persistés peu fréquemment. Cf. `GPS_TRACKING.md`.
- **Autorisation des canaux (correctif de sécurité — obligatoire) :** les canaux
  **Broadcast**/**Presence** n'ont **pas** de table sous‑jacente → la RLS des
  tables **ne les protège pas**. Tous les canaux `mission:{id}:*` sont **privés**
  et autorisés par **Realtime Authorization** : une policy RLS sur
  `realtime.messages` n'autorise `read`/`write` sur `topic = 'mission:{id}:*'`
  **que** si `auth.uid()` est **participant** de la mission `{id}` (client ou
  intervenant assigné) — vérifié via une fonction `is_mission_participant(id)`.
  Idem `operator:review-inbox`/`operator:presence` : réservés aux rôles
  `operator`/`admin`. **Aucun** abonnement inter‑missions possible.
- Pour Postgres Changes, la RLS des tables sources s'applique **en plus**.

---

## 8. Autorisation — matrice (extrait)

| Opération | client | operator | admin |
|---|---|---|---|
| classifier / estimer / zone‑check | ✅ (les siennes) | ✅ | ✅ |
| soumettre une demande | ✅ | — | ✅ |
| **accepter/refuser/need_info** | ❌ | ✅ | ✅ |
| fixer le prix (custom) | ❌ | ✅ | ✅ |
| autoriser le paiement | ✅ (si `accepted`) | ❌ | ✅ |
| capturer / clôturer | ❌ | ✅ (assigné) | ✅ |
| remboursement exceptionnel | ❌ | ❌ | ✅ |
| étapes d'exécution | ❌ | ✅ (assigné) | ✅ |
| éditer catalogue/questions/tarifs/config/textes | ❌ | ❌ | ✅ |

> Toute règle ci‑dessus est **doublée en RLS** (défense en profondeur), pas
> seulement au niveau applicatif.

---

## 9. Sécurité & robustesse

- **JWT** vérifié par le runtime (`verify_jwt=true`) sauf sondes/webhooks signés.
- **Webhooks** (ex. Stripe futur) : signature vérifiée avant traitement.
- **Idempotence** sur paiement, transitions à effets, push.
- **Rate limiting** : OTP (Auth), `classify-request` (coût IA) via `app_config`.
- **Validation serveur** systématique des réponses dynamiques (jamais confiance
  au client) : `questions.validation` + `required_when`.
- **Secrets** en Vault/env ; jamais dans l'app.

## 10. Évolutivité (P0/P2)

- **Nouveau métier** = données (catégorie + `capability_classification` + questions
  + `category_workflow` + tarifs + templates). **Aucun** changement d'API : les
  mêmes endpoints (`classify-request`, `converse`, `questions`, `submit-request`,
  `review-request`, paiement) s'appliquent — le dialogue s'adapte via la donnée.
- **Stripe** remplace le `mock` derrière `PaymentProvider` : contrats §4.6–4.8
  **inchangés**.
- **Multi‑intervenant** : `assign-mission` passe d'auto à dispatch ; contrats
  clients inchangés.

## 11. Références

`PRD.md` · `BUSINESS_RULES.md` · `SPEC_FONCTIONNELLE_V1.md` · `DATA_MODEL.md` ·
`UX_SPEC.md` · `Architecture_Technique.md` · à venir : `ADMIN_PANEL.md`,
`GPS_TRACKING.md`, `NOTIFICATIONS.md`, `CHAT.md`.
