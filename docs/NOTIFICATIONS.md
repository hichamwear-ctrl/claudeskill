# NOTIFICATIONS — Système de notifications — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **But :** un système de notifications **100 % piloté par la donnée** (types,
> textes, déclencheurs, canaux **en base**), cohérent avec le **contrôle humain**
> (P1) et **extensible sans code** (P2).
>
> **Cohérence :** `Architecture_Technique.md` (§14), `DATA_MODEL.md`, `API_SPEC.md`,
> `SPEC_FONCTIONNELLE_V1.md` (§6), `CONVERSATION_ENGINE.md`, `CONFIG_VERSIONING.md`.

---

## 1. Principes

- **Data‑driven.** Une notification = **`notification_triggers`** (événement →
  template) + **`notification_templates`** (audience, canal) + **`content_strings`**
  (textes i18n). Ajouter/modifier/désactiver une notification = **données**
  (versionnées via `CONFIG_VERSIONING.md`), **jamais** de code.
- **Reflète le contrôle humain (P1).** Les notifications **traduisent** des
  décisions (opérateur accepte/refuse/demande) et des transitions d'état ; elles
  ne **déclenchent** aucune décision ni paiement.
- **Respectueux.** Consentement, préférences par type, **silence nocturne** (sauf
  mission active), anti‑spam, deep‑link vers le bon écran.
- **Fiable.** **Idempotence** (clé d'événement), nettoyage des jetons, i18n.

---

## 2. Architecture de bout en bout

```
Transition d'état / événement en base
  → Database Webhook (pg_net)
  → Edge Function `send-push`
       1. résout notification_triggers (event_key → templates actifs, condition)
       2. pour chaque template : audience, canal, textes via content_strings (locale)
       3. applique préférences + silence nocturne + idempotence
       4. écrit `notifications` (in-app) + envoie Expo Push (device_tokens)
  → Appareil(s) (APNs/FCM) · Liste in-app · (Realtime badge)
```

- **Source d'événements :** `mission_events` (transitions), plus événements
  applicatifs (nouveau message, position « proche », retard détecté par cron).
- **Canaux V1 :** **push** (Expo) + **in‑app** (`notifications`). **Extensible**
  (email/SMS) par ajout de canal en donnée (V2).

---

## 3. Déclencheurs — `notification_triggers`

- **Rôle :** mapping **événement → template(s)**, éditable.
- **Colonnes :** `id`, `event_key`, `template_key`, `audience`, `condition jsonb?`
  (mini‑langage borné), `is_active`, `sort_order`.
- **Clés d'événement (`event_key`) — convention :**
  `mission.status.<statut>` (ex. `mission.status.accepted`),
  `mission.event.<nom>` (ex. `mission.event.nearby`, `mission.event.delayed`,
  `mission.event.receipt`), `chat.message`, `quote.expired`, `review.new`.
- **💡** Ajouter une notification sur un événement existant = **insérer une ligne**.

## 4. Modèles — `notification_templates`

- **Rôle :** gabarit par type & audience.
- **Colonnes :** `key`, `audience ('client'|'operator'|'admin')`, `channel
  ('push'|'inapp'|'both')`, `title_key`, `body_key` (→ `content_strings`),
  `deep_link_template?`, `is_active`, `metadata jsonb` (dont
  `bypass_quiet_hours: bool`, `group_key?`, `priority?`) — **PK `(key, audience)`**.
- **Variables** disponibles dans les gabarits : `{operator}`, `{eta}`,
  `{final_amount}`, `{price}`, `{reason}`, `{sender}`, `{category}`, `{distance}`…
  (résolues au rendu).

---

## 5. Catalogue complet (V1)

> Catalogue **initial** ; il vit en base et s'enrichit sans code. Référence
> fonctionnelle : `SPEC_FONCTIONNELLE_V1.md` §6.

### 5.1 Destinataire CLIENT
| `type` (template_key) | `event_key` | Canal | Deep‑link | Nuit* |
|---|---|---|---|---|
| `request_submitted` | `mission.status.pending_review` | both | suivi demande | non |
| `request_accepted` | `mission.status.accepted` | both | paiement | **oui** |
| `request_rejected` | `mission.status.rejected` | both | détail | non |
| `request_needs_info` | `mission.status.needs_information` | both | conversation | **oui** |
| `operator_at_store` | `mission.status.shopping` | push | suivi | **oui** |
| `shopping_done` | `mission.event.shopping_done` | push | suivi | **oui** |
| `mission_preparing` | `mission.status.preparing` | push | suivi | **oui** |
| `mission_en_route` | `mission.status.en_route` | push | carte | **oui** |
| `operator_nearby` | `mission.event.nearby` | push | carte | **oui** |
| `mission_arrived` | `mission.status.arrived` | push | carte | **oui** |
| `mission_completed` | `mission.status.completed` | both | reçu | **oui** |
| `receipt_available` | `mission.event.receipt` | inapp | reçu | non |
| `mission_delayed` | `mission.event.delayed` | push | suivi | **oui** |
| `intervention_impossible` | `mission.status.failed` | both | détail | **oui** |
| `refund_simulated` | `mission.event.refund` | both | paiement | non |
| `mission_cancelled` | `mission.status.cancelled` | both | détail | **oui** |
| `price_expired` | `quote.expired` | both | nouvelle demande | non |
| `rating_request` | `mission.status.completed` (différé) | push | notation | non |
| `chat_message` | `chat.message` | push | chat | **oui** |

\* **Nuit = oui** : autorisé pendant le silence nocturne **car lié à une mission
active** (`metadata.bypass_quiet_hours`).

### 5.2 Destinataire OPÉRATEUR
| `type` | `event_key` | Canal | Deep‑link |
|---|---|---|---|
| `new_request_to_review` | `review.new` (`mission.status.pending_review`) | both | file de revue |
| `mission_new` | `mission.status.assigned` | push | mission |
| `mission_cancelled_by_client` | `mission.event.cancelled_by_client` | push | mission |
| `chat_message` | `chat.message` | push | chat |

### 5.3 Destinataire ADMIN (exploitation)
| `type` | `event_key` | Canal |
|---|---|---|
| `dispute_opened` | `dispute.opened` | inapp/email(V2) |
| `review_backlog` | `review.backlog` (cron : file trop longue) | inapp |
> Types admin **optionnels**, activables par donnée.

---

## 6. Canaux & livraison

- **Push (Expo)** : jetons dans `device_tokens` (multi‑appareils) ; envoi via Expo
  Push (APNs/FCM). Nettoyage des jetons invalides (retour Expo).
- **In‑app** : ligne `notifications` (liste C‑28, badge Realtime).
- **Futur (V2)** : email/SMS — nouveau **canal en donnée** (template `channel`),
  sans refonte.

## 7. Idempotence & fiabilité

- **Clé d'idempotence** par (event unique, template, destinataire) → **aucun
  doublon** même en cas de re‑livraison de webhook.
- **Retry** borné côté `send-push` ; échec loggé (observabilité).
- **Ordonnancement** : `rating_request` **différé** (délai `app_config.notif.*`).

## 8. Préférences, consentement & silence nocturne

- **Consentement** : permission push (UX C‑06) ; journalisé (RGPD).
- **Préférences par type/canal** : `notification_preferences` (**nouvelle table**,
  optionnelle) — `user_id`, `type`, `channel`, `enabled`. Défauts dans les
  templates ; l'utilisateur **surcharge** (ex. couper `rating_request`).
  Les types **critiques** liés à une mission active ne sont pas désactivables.
- **Silence nocturne** : `app_config.notifications.quiet_hours`
  (`{"from":"22:00","to":"07:00"}`) + override utilisateur ; **bypass** si
  `template.metadata.bypass_quiet_hours` (mission active).
- **Anti‑spam / groupement** : `metadata.group_key` (regrouper plusieurs messages
  chat) ; fréquence bornée (`app_config.notif.min_interval_sec`).

## 9. Deep‑links

- Chaque template porte un `deep_link_template` (ex.
  `app://mission/{mission_id}`, `app://conversation/{conversation_id}`,
  `app://review/{mission_id}`) → ouverture directe du bon écran (`UX_SPEC`).

## 10. i18n

- Titres/corps via **`content_strings`** (locale du profil, défaut `fr`) ; aucune
  copie codée en dur → éditable et **versionnée**.

## 11. Sécurité & RGPD

- **RLS** : `notifications` (destinataire seul), `device_tokens` (propriétaire),
  `notification_preferences` (propriétaire) ; écriture serveur (`send-push`).
- **PII** : pas d'info sensible superflue dans les push (contenu minimal +
  deep‑link) ; rétention des notifications configurable (purge `pg_cron`).
- **Secrets** (clé Expo) côté serveur.

## 12. Évolutivité (sans refonte)

- **Nouvelle notification** = insérer `notification_templates` + `notification_
  triggers` + `content_strings` (versionné). Aucun code.
- **Nouveau canal** (email/SMS) = valeur `channel` + adaptateur d'envoi générique.
- **Ciblage** (par rôle/zone/%) via `feature.*` / `condition` — A/B possible.
- **Nouvel événement** : émettre un `event_key` (transition/trigger DB) que des
  triggers peuvent écouter.

## 13. Impacts modèle de données

- **Réutilise** : `notification_templates`, `notification_triggers`,
  `notifications`, `device_tokens`, `content_strings`, `app_config`.
- **Ajoute (optionnel) :** `notification_preferences` (surcharge par utilisateur)
  + clés `app_config.notifications.*` (quiet_hours, min_interval, délais).
- **Versionnement :** `notification_templates`/`_triggers` sont des **modules de
  configuration** (registre `config_modules`).

## 13bis. Implémentation V1 (M8)

> **🔧 4 tables** (`notification_templates`, `notification_triggers`,
> `notifications`, `device_tokens`) — `notification_preferences` **différée**
> (optionnelle). **1 Edge Function** `send-push` = **transport pur** (mock Expo →
> Expo/FCM/APNS/email/SMS via `NOTIFY_TRANSPORT`).
>
> Toute la résolution data-driven vit dans la RPC **`dispatch_notifications`**
> (`event_key`, `context`) : triggers → templates → `content_strings` (locale) →
> rendu (`{variables}`) → écriture idempotente de `notifications`, puis renvoi de
> la liste à pousser (jetons `device_tokens`). **Idempotence** = `notifications.
> dedup_key` UNIQUE = `source_ref:template:audience:user`. **Silence nocturne** &
> **`min_interval`** appliqués en base (`app_config.notifications.*`), **bypass**
> par `template.metadata.bypass_quiet_hours`. Absences (trigger/template/
> `content_strings`) → **skip gracieux** (aucun crash). L'émetteur n'est jamais
> auto-notifié. Deep-links : `mission`/`chat`/`conversation`/`payment`/`review`.
> Les **Database Webhooks** (branchés ultérieurement) appellent `send-push` sur
> `mission_events`/`messages`/`payments`/review — sources déjà en place (M4–M7).

## 14. Cohérence & références

- Types alignés avec `SPEC_FONCTIONNELLE_V1.md` §6 ; déclencheurs sur transitions
  de `mission_events` ; `chat_message` cf. `CHAT.md` (à venir) ;
  `operator_nearby`/`mission_arrived` cf. `GPS_TRACKING.md`.
- Contrôle humain : `new_request_to_review` (opérateur) sur `pending_review` ;
  `request_accepted` **débloque** le paiement (jamais l'inverse).
- Références : tous les documents `docs/`.
