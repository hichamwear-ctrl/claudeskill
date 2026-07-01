# LEAN V1 — Architecture cible vs implémentation V1 — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **But :** garder une **architecture cible ambitieuse** (tous les concepts
> validés) tout en **implémentant en V1 le strict nécessaire**. On **diffère**
> l'implémentation, on ne **supprime jamais** un concept.
>
> **Règle de gouvernance :** un élément « différé » **reste** dans la
> documentation cible (`DATA_MODEL.md`, `Architecture_Technique.md`…). Il sera
> activé par une **migration additive** quand son **déclencheur métier** arrive —
> **sans refonte** (c'est tout l'objet du modèle data‑driven). Ce document est la
> **feuille de route d'implémentation** ; la doc cible reste la référence.

---

## 0. Correctifs bloquants (intégrés — cible **et** V1)

| Correctif | Statut | Où |
|---|---|---|
| **Autorisation des canaux Broadcast/Presence** (canaux privés + policy `realtime.messages` = participant de la mission) | ✅ intégré | `API_SPEC` §7, `Architecture` §10, `GPS_TRACKING` §9, `CHAT` §3 |
| **Claim de revue opérateur** (`review_claimed_by/at`, RLS file non‑claimée + `review-claim`) | ✅ intégré | `API_SPEC` §4.4b, `DATA_MODEL` missions, `Architecture` §9, `BUSINESS_RULES` BR‑002 |
| **Versionnement d'API** (`X‑Api‑Version`, additif, canaux stables) | ✅ intégré | `API_SPEC` §2.1, `Architecture` §10 |

> Ces trois points sont **implémentés en V1** (sécurité/robustesse), même si le
> claim ne devient critique qu'en multi‑opérateur : les **colonnes + la RLS** sont
> posées dès V1 (coût quasi nul, évite une migration sensible plus tard).

---

## 1. Tables — cible (44) vs V1 vs différé

### 1.1 Créées en V1 (~26 — cœur strictement nécessaire à la démo de bout en bout)

| Domaine | Tables V1 |
|---|---|
| Identité | `profiles`, `operator_profiles`, `device_tokens`, `addresses` |
| Référentiel/zones ✅ *(M1.1/M1.2 déjà livrés)* | `service_categories`, `coverage_zones`, `service_windows`, `waitlist` |
| Config & contenu | `app_config`, `content_strings` |
| Workflow | `category_workflow` |
| Questions (moteur) | `question_sets`, `questions`, `question_options` |
| Conversation | `conversations`, `conversation_turns` |
| Cœur | `missions`, `mission_events` |
| Tarif | `pricing_rules` |
| Paiement (sim) | `payments` |
| Temps réel | `operator_locations` *(M7 ; `mission_tracks` différée)* |
| Chat | `messages` |
| Notifications | `notifications`, `notification_templates`, `notification_triggers` |
| Avis | `ratings` |
| Audit | `audit_log` |

> Colonnes **absorbant** des tables différées (pour ne pas perdre la fonction en
> V1) : `missions` porte `quoted_price`/`quote_expires_at`/`quote_status`
> (au lieu de `quotes`), `advance_estimate`/`advance_actual` (au lieu d'`advances`),
> `tip_amount` (au lieu de `tips`), et `details jsonb` (au lieu de `mission_items`).

### 1.2 Différées (concept **conservé** en cible, **non créées** en V1)

| Table(s) | Statut | Justification du report |
|---|---|---|
| `capabilities`, `category_capabilities`, `capability_classification` | 🔜 cible | En V1, la classification **texte → catégorie** (6 catégories) + **fallback générique** (`category_id=null`) produit le **même comportement visible**. L'abstraction « capacités » (P7) paie quand les métiers se **multiplient et se recouvrent** : on l'active alors sans refonte (le moteur composera les questions par capacité). |
| `mission_transitions` | 🔜 cible | Les **effets** de transition restant en **code**, une allow‑list **en code** suffit en V1 (plus simple, plus sûre). On externalise en table quand on voudra **éditer le graphe** sans redéploiement. |
| `pricing_modifiers` | 🔜 cible | Aucun **supplément** (nuit/week‑end/urgence…) en V1 : `pricing_rules` + `service_categories.base_fee` suffisent. Table activée à l'apparition du 1ᵉʳ supplément. |
| `mission_tracks` | 🔜 cible | **Différée en M7** : un tracé GPS persisté = historique/preuve/analytics (hors périmètre V1 « pas de tracking permanent ») et des centaines de milliers d'écritures/jour. Le live passe par Broadcast, la dernière position par `operator_locations`. Ajoutée sans refonte (consommateur du Broadcast) quand un besoin réel émerge. |
| `quotes` | 🔜 cible | 1 prix proposé/mission en V1 → **colonnes sur `missions`**. Table dédiée quand on voudra **historiser** plusieurs devis/révisions. |
| `mission_items` | 🔜 cible | La liste d'articles est une **réponse** comme une autre → `missions.details` (jsonb) en V1. Table dédiée si un jour on requête/agrège les articles finement. |
| `advances` | 🔜 cible | `missions.advance_estimate/advance_actual` + reçu dans `mission-proofs` couvrent la V1. Table dédiée pour un **suivi comptable** détaillé des avances. |
| `tips` | 🔜 cible | Pourboire **simulé**, 1/mission → colonne. Table dédiée pour l'historique/reversement (Stripe V2). |
| `disputes` | 🔜 cible | V1 : litige = `admin` + `refund` (sim) + `metadata`. Table dédiée quand un **workflow de litige** (instruction/arbitrage) est nécessaire. |
| `payment_methods` | 🔜 cible | Paiement **mock** : aucune carte à stocker. Table utile avec **Stripe réel** (V2). |
| `payouts`, `promo_codes` | 🔜 V2 | Reversements intervenants (Stripe Connect) et promotions : **hors V1** par décision produit. |
| `notification_preferences` | 🔜 cible | Défauts dans les **templates** suffisent en V1. Table activée pour les **surcharges par utilisateur**. |
| `config_modules`, `config_versions`, `config_snapshots` | 🔜 cible | V1 a **peu de config** et **un seul admin** ; `audit_log` couvre la traçabilité. Le **versionnement** (Brouillon→Publication→Rollback) s'active quand le **volume de config / la taille d'équipe** le justifient — **sans refonte** (registre générique). |

> **Total :** ~25 créées en V1 · ~19 différées (concept conservé, dont
> `mission_tracks` déplacée en M7) · **44 cible**.

---

## 2. Edge Functions — cible vs V1

### 2.1 V1 (~7 fonctions robustes + 1 RPC + 1 trigger)

| Fonction V1 | Rôle | Consolidation |
|---|---|---|
| `converse` | dialogue (extraction + prochaine question) **incluant la classification du 1ᵉʳ tour** | absorbe `classify-request` |
| `zone-check` ✅ | couverture + horaires (RPC `zone_check`, PostGIS) | — |
| `estimate-price` ✅ | prix + ETA (RPC `estimate_price`, PostGIS + `pricing_rules`) | — |
| `submit-request` ✅ | **V1 :** revalidation serveur + **création atomique d'1 mission `pending_review`** (RPC `create_mission_from_conversation`) + conversation `submitted`. Garde‑fou P1 (aucun paiement/décision). Multi‑services `group_id` différé | 1 mission/conversation en V1 |
| `review` ✅ | **claim + décision** (`claim_review` / `transition_mission`) | absorbe `review-claim` + `review-request` |
| `payments` ✅ | **authorize / capture / refund / void** (mock, gaté `accepted`) via `payment_intent`/`payment_settle` | absorbe `create-authorization`/`capture-payment`/`refund` |
| `send-push` ✅ | **transport pur** ; résolution data-driven via RPC `dispatch_notifications` (idempotence `dedup_key`) | — |
| `transition_mission` *(RPC DB)* ✅ | machine à états (allow‑list **en code** V1 ; `mission_transitions` différée) + `claim_review` + `create_mission_from_conversation` | — |
| `assign_mission` *(RPC DB)* ✅ | affectation auto après autorisation | **fondue dans `payment_settle`** (ni Edge ni trigger) |

### 2.2 Différées

| Fonction | Statut | Justification |
|---|---|---|
| `classify-request` (séparée) | 🔜 cible | Séparée seulement si la classification devient un service réutilisé hors dialogue ; sinon interne à `converse`. |
| `config-create-draft` / `config-validate` / `config-publish` / `config-rollback` | 🔜 cible | Avec le **versionnement de configuration** (différé §1.2). |

> **Note contrats :** `API_SPEC.md` documente les fonctions **par capacité**
> (create-authorization, capture-payment…). En V1, elles sont **regroupées** en
> `payments`/`review` via un paramètre `action` — **mêmes contrats logiques**,
> moins de surface de déploiement. La cible peut les éclater si besoin.

---

## 3. Enums — V1 vs cible

- **V1 :** `user_role`, `mission_family`, `mission_status` (avec `pending_review`/
  `needs_information`/`rejected`/`shopping` ; `searching` réservé), `payment_status`,
  `operator_status`, `cancel_actor`, `question_type`, `conversation_status`.
- **Différés (avec leur table) :** `quote_status` (avec `quotes`), `dispute_status`
  (avec `disputes`), `config_version_status` (avec le versionnement).
  → En V1, `missions.quote_status` peut être un **texte contraint** en attendant.

---

## 4. Correspondance avec la roadmap (M‑étapes)

| Étape | Contenu V1 | Tables/fonctions V1 concernées |
|---|---|---|
> **Rythme (mis à jour) :** depuis les fondations verrouillées, on avance par
> **modules complets** (un rapport de validation par module), et non plus par
> micro‑étapes. Numérotation consolidée ci‑dessous.

| Étape | Contenu V1 | Tables/fonctions V1 concernées |
|---|---|---|
| **M1** ✅ | fondations : catalogue, zones/horaires, tarif & config, i18n | `service_categories`, `coverage_zones`, `service_windows`, `waitlist`, `pricing_rules`, `app_config`, `content_strings` |
| **M2** ✅ | conversation & questions + **moteur pur** | `conversations`, `conversation_turns`, `question_*` ; `_shared/engine/` (compute déterministe) |
| **M3** ✅ | **moteur conversationnel opérationnel** | `converse`, `submit-request`, `_shared/intake/` (orchestration + store + classifieur mots‑clés), seed `classification.keywords` |
| **M4** ✅ | **missions & revue opérateur** | `missions` (+ colonnes absorbées), `mission_events`, `category_workflow` ; RPC `transition_mission`/`claim_review`/`create_mission_from_conversation`/`estimate_price`/`zone_check` ; Edge `review`/`estimate-price`/`zone-check` ; `submit-request` crée la mission |
| **M5** ✅ | **paiement simulé (Stripe‑ready)** | table `payments` ; RPC `payment_intent`/`payment_settle`/`assign_mission` ; Edge `payments` ; `_shared/payments/` (interface `PaymentProvider` + `MockPaymentProvider`) |
| **M6** ✅ | **chat d'exécution** | table `messages` (append-only, modération, RLS participants) ; RPC `mark_messages_read` ; **autorisation Realtime** (`can_access_topic`, `is_mission_participant`, `owns_conversation`, policies `realtime.messages`) ; **0 Edge Function** |
| **M7** ✅ | **temps réel (GPS)** | table `operator_locations` ; RPC `update_location`/`get_operator_location` ; purge auto (trigger) ; `can_publish_topic` (durcissement Realtime) ; clés `gps.*` ; **0 Edge Function** ; `mission_tracks` différée |
| **M8** ✅ | **notifications** | `notifications`, `notification_templates`, `notification_triggers`, `device_tokens` ; RPC `dispatch_notifications`/`render_template`/`mark_*_read` ; Edge `send-push` (transport enfichable) ; catalogue seedé |
| **M9+** | admin, config versioning, litiges… | panneau admin, `config_*`, `disputes` |
| **M9** | notifications | `notifications`, `notification_templates/triggers`, `send-push` |
| **M10** | storage métier | policy participant `mission-proofs` |
| **M11** | avis | `ratings` |
| **M12** | admin (V1 light) | lecture/édition config existante + `audit_log` |
| **M13** | durcissement | tests RLS, RGPD |

> Les modules différés (capacités, versionnement, litiges…) s'insèrent après la
> V1 par **migrations additives**, chacun déclenché par son besoin métier.

---

## 5. Verdict

- **Architecture cible :** inchangée, ambitieuse, **tous les concepts conservés**.
- **Implémentation V1 :** **~26 tables** et **~7 Edge Functions** — conforme à la
  philosophie « supprimer/différer plutôt qu'ajouter », sans perdre **aucune**
  fonction produit visible de la démo.
- **Correctifs bloquants :** intégrés (Broadcast, claim, versionnement d'API).

**Prête à coder** dès validation de ce périmètre : M1.3 reprend sur `pricing_rules`
+ `app_config` + `content_strings`.

## 6. Références
Tous les documents `docs/` (la **cible**). Ce document est la **feuille de route
d'implémentation V1** ; en cas de doute d'implémentation, il prime ; en cas de
doute sur la **cible**, les documents de domaine priment.
