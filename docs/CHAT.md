# CHAT — Chat d'exécution de mission — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Portée :** le **chat d'exécution** entre **client et intervenant**, pendant une
> mission **active**. **Ce n'est PAS** la conversation d'intake.
>
> **Principe P9 (séparation stricte) :** la **conversation d'intake**
> (`CONVERSATION_ENGINE.md` : comprendre le besoin → `pending_review`) et le
> **chat de mission** (ce document) sont **deux systèmes totalement indépendants**
> — **tables, règles métier et notifications distinctes**. Ils ne partagent rien.
>
> **Cohérence :** `Architecture_Technique.md`, `DATA_MODEL.md`, `API_SPEC.md`,
> `NOTIFICATIONS.md`, `BUSINESS_RULES.md`, `UX_SPEC.md`.

---

## 1. Séparation stricte intake ≠ exécution (P9)

| Aspect | Conversation d'intake | **Chat de mission (ce doc)** |
|---|---|---|
| Objectif | comprendre le besoin, poser des questions, constituer le dossier | **communiquer pendant l'exécution** d'une mission acceptée |
| Participants | client ↔ **moteur/IA** | client ↔ **intervenant** (humains) |
| Quand | **avant** `pending_review` (+ reprise en `needs_information`) | **après** acceptation, mission **active** |
| Tables | `conversations`, `conversation_turns` | **`messages`** |
| Règles | moteur conversationnel (capacités, slots, P7/P8) | messagerie simple (envoi/lecture/typing/modération) |
| Notifications | `new_request_to_review` (à la soumission) | **`chat_message`** (exécution) |
| IA | centrale (prépare) | **aucune** (échange humain direct) |
| Fin | `submitted` → l'IA s'arrête | à la clôture de la mission |

> **Aucune fonction, table, règle ou notification n'est partagée** entre les deux.

---

## 2. Cycle de vie

```
mission acceptée → assignée (intervenant affecté)
   → CHAT OUVERT (client ↔ intervenant)
   → pendant shopping / preparing / en_route / arrived / in_progress
   → mission completed / cancelled / failed → CHAT FERMÉ (lecture seule, rétention)
```

- **BR‑CHAT‑01 :** le chat n'existe **qu'à partir de l'affectation** (`assigned`)
  et pour une mission **active**. **Jamais** avant l'acceptation (P1) ni pour une
  demande en `pending_review`/`needs_information` (→ ça, c'est l'intake).
- **BR‑CHAT‑02 :** à la clôture, le fil passe en **lecture seule** (conservé selon
  la rétention) ; plus d'envoi.

---

## 3. Architecture temps réel

| Canal | Type | Usage |
|---|---|---|
| `mission:{id}:chat` | **Postgres Changes** sur `messages` | nouveaux messages (persistés) |
| `mission:{id}:typing` | **Broadcast** (éphémère) | indicateur « en train d'écrire » |

- Messages **persistés** (contrairement aux positions GPS) → `messages` + Postgres
  Changes. **RLS** garantit que seuls les **2 participants** reçoivent le fil.
- Typing via **Broadcast** (pas d'écriture DB) → **canal privé** autorisé par une
  policy `realtime.messages` (participant de la mission uniquement) — Broadcast
  n'étant pas couvert par la RLS des tables (cf. `API_SPEC.md` §7).

---

## 4. Données

### `messages` (réutilisée — cf. `DATA_MODEL.md` §7.1)
- `id`, `mission_id`, `sender_id`, `body`, `read_at?`, `media jsonb?`,
  `metadata jsonb` (modération), `created_at`.
- **Index :** `(mission_id, created_at)` ; **partitionnement mensuel**.
- **RLS :** lecture/écriture réservées aux **participants de la mission**
  (client + intervenant assigné) ; insert `sender_id = auth.uid()` **et** membre
  de la mission. Admin en lecture (support/litige).
- **Aucune** colonne partagée avec `conversation_turns` (systèmes distincts).

---

## 5. Fonctionnalités

- **Envoi** de messages texte ; **médias** optionnels (photo) selon
  `app_config.chat.allow_media` (upload Storage, scoping mission).
- **Accusés de lecture** : `read_at` mis à jour à l'ouverture du fil.
- **Indicateur de frappe** : Broadcast `typing`.
- **Messages système** (optionnels) : jalons de mission (« en route », « arrivé »)
  injectés comme entrées `metadata.system=true` — **cosmétique**, sans logique
  métier (la vérité reste `mission_events`).
- **Écrans :** C‑20 (client), OP‑10 (intervenant).

---

## 6. Modération & conformité

- **BR‑CHAT‑10 Anti‑coordonnées :** filtre (Edge/trigger) détectant téléphone/
  e‑mail/liens pour **protéger le masque** et la vie privée ; action configurable
  (`app_config.chat.moderation` : masquer / avertir / bloquer).
- **BR‑CHAT‑11 :** signalement d'un message → dossier `disputes`/support (admin).
- **RGPD :** rétention configurable (`app_config.chat.retention_days`), purge
  `pg_cron` ; suppression avec le compte.

---

## 7. Notifications (exécution uniquement)

- **`chat_message`** (cf. `NOTIFICATIONS.md`) : envoyée au **destinataire** quand
  un message arrive et que l'app est en arrière‑plan ; **groupement**
  (`metadata.group_key`) ; deep‑link vers C‑20/OP‑10.
- Cette notification appartient **exclusivement** au chat d'exécution ; l'intake
  n'en émet **aucune** (P9).

---

## 8. Sécurité & vie privée

- **RLS participants** stricte ; aucun tiers ne lit le fil.
- **Numéro masqué** (V2, Twilio) pour les appels ; en V1 l'appel est **simulé**.
- **Minimisation** : pas de PII superflue ; médias privés (URLs signées).
- **Secrets** côté serveur.

---

## 9. Piloté par la configuration (`app_config.chat.*`)

| Clé | Rôle | Défaut |
|---|---|---|
| `chat.allow_media` | autoriser les photos | true |
| `chat.moderation` | politique anti‑coordonnées | `mask` |
| `chat.retention_days` | rétention des messages | 90 |
| `chat.max_len` | longueur max d'un message | 2000 |
| `chat.read_receipts` | accusés de lecture | true |

> Comportement ajustable **sans code** ; **versionné** (`CONFIG_VERSIONING.md`).

---

## 10. Évolutivité (sans refonte)

- **Canaux additionnels** (pièces jointes, localisation ponctuelle partagée) via
  `metadata`/config.
- **Traduction automatique** des messages (client/intervenant de langues
  différentes) — activable par `feature.*`, sans changer le modèle.
- **Modération avancée** (règles éditables) — table dédiée **si** besoin
  (registre `config_modules`).

---

## 11. Impacts modèle de données

- **Réutilise** `messages` (déjà au modèle). **Aucune** nouvelle table en V1.
- **Ajoute** des clés `app_config.chat.*` (§9).
- **Ne touche pas** `conversations`/`conversation_turns` (systèmes séparés, P9).

> **🔧 Implémentation V1 (M6) :** **zéro Edge Function**. Envoi = `INSERT` gardé par
> la RLS (participant + `sender_id=self` + mission `assigned…in_progress`) + trigger
> `moderate_message` (déterministe : email/tél/URL selon `chat.moderation`, borne
> `chat.max_len`). Table **append-only** (aucune UPDATE/DELETE) ; `read_at` via RPC
> `mark_messages_read` (destinataire uniquement). Temps réel : **Postgres Changes**
> (messages persistés, RLS) + **Broadcast** (frappe). Sécurité des canaux :
> `can_access_topic` (fail-closed) sur `realtime.messages` — couvre chat, typing,
> statut et **position GPS (M7)**. Évolutivité sans migration : `media jsonb`
> (pièces jointes/photos/vocaux), `kind` (system/appels), `body` nullable
> (message média seul), `metadata` (chiffrement futur).

## 12. Cohérence & références

- **P9 respecté** : chat d'exécution 100 % distinct de l'intake (tables/règles/
  notifs séparées).
- **P1** : le chat n'ouvre qu'après acceptation humaine et affectation.
- Références : `CONVERSATION_ENGINE.md` (l'autre système), `DATA_MODEL.md` §7.1,
  `NOTIFICATIONS.md` (`chat_message`), `GPS_TRACKING.md`, `Architecture_Technique.md`
  §12.
