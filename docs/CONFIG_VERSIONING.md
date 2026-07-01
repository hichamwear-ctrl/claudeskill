# CONFIG VERSIONING — Versionnement de la configuration — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **But :** versionner **toute la configuration métier** de la plateforme (pas
> seulement `app_config`) et permettre **Brouillon → Validation → Publication →
> Rollback en un clic**, **sans jamais toucher au code** (P2). Système **générique**
> : ajouter un nouveau module de configuration = **une ligne de registre**, pas de
> modification de l'architecture de versionnement.
>
> **Cohérence :** `Architecture_Technique.md`, `DATA_MODEL.md`, `ADMIN_PANEL.md`,
> `API_SPEC.md`, `BUSINESS_RULES.md`.

---

## 1. Périmètre : configuration ≠ opérationnel

- **Versionné (configuration de la plateforme) :** capacités (`capabilities`,
  `category_capabilities`), taxonomie (`service_categories`), classification
  (`capability_classification`), questions
  (`question_sets`/`questions`/`question_options`), workflows
  (`category_workflow`), transitions (`mission_transitions`), tarifs
  (`pricing_rules`/`pricing_modifiers`), zones (`coverage_zones`), horaires
  (`service_windows`), paramètres (`app_config`), notifications
  (`notification_templates`/`notification_triggers`), templates de conversation
  (via `content_strings` + `app_config.conversation.*`), contenus
  (`content_strings`), et **tout futur module** de configuration.
- **JAMAIS versionné (données opérationnelles) :** `missions`, `conversations`,
  `conversation_turns`, `payments`, `messages`, `profiles`, `operator_profiles`,
  `addresses`, `ratings`, `disputes`, `mission_events`, `audit_log`,
  `operator_locations`, `mission_tracks`, `device_tokens`, `waitlist`.

> **Règle stricte :** seul ce qui est **déclaré dans le registre** (`config_modules`)
> est versionné. Les tables opérationnelles n'y figurent **jamais** — garantie
> structurelle (un garde‑fou refuse d'enregistrer une table non‑config).

---

## 2. Principes de conception

1. **Générique par registre.** Un **registre** liste les tables de configuration.
   Le moteur de versionnement **itère le registre** : ajouter un module =
   **insérer une ligne**, aucune modification de code du moteur.
2. **Stockage agnostique du schéma.** Un snapshot est du **JSONB** (les lignes de
   chaque table de config). Une nouvelle table est versionnable **sans migration**
   du système de versions.
3. **Live = version publiée.** L'application lit **toujours** les tables de config
   « live », qui correspondent à la **version publiée**. Pas de résolveur complexe
   à l'exécution : la publication **matérialise** la config dans les tables live.
4. **Brouillon isolé.** Les modifications se font sur un **brouillon** (isolé de la
   prod) ; rien n'affecte le live tant qu'on n'a pas **publié**.
5. **Intégrité préservée.** Les **identifiants** (PK) sont **stables** entre
   versions ; la suppression logique (`is_active=false`) est privilégiée à la
   suppression physique → les données opérationnelles qui référencent la config
   (ex. `missions.category_id`) **restent valides** après un rollback.
6. **Sécurité & audit.** Réservé `admin` (RLS) ; chaque étape est tracée
   (`audit_log`) ; certaines règles restent **non désactivables** (P0/P1/RLS).
7. **Transactionnel & ordonné.** Publication/rollback appliqués en **une
   transaction**, dans l'**ordre de dépendances** du registre.

---

## 3. Cycle de vie

```
        create draft (copie de la version publiée)
             │
        ┌────▼─────┐  éditions (back-office) sur le BROUILLON isolé
        │  DRAFT   │◀───────────────────────────────────────────┐
        └────┬─────┘                                             │ modifier
   validate  │  (checks: schéma + intégrité + simulateurs)       │
        ┌────▼──────┐   échec → retour DRAFT ──────────────────-─┘
        │ VALIDATED │
        └────┬──────┘
     publish │  (matérialise le brouillon dans les tables live, transactionnel)
        ┌────▼───────┐
        │ PUBLISHED  │  ← version active (le live)
        └────┬───────┘
    rollback │  (re-publie une version antérieure = restaure son snapshot)
        ┌────▼───────┐
        │ ARCHIVED   │  (versions non actives, conservées pour rollback/historique)
        └────────────┘
```

- **Brouillon (`draft`)** : espace de travail isolé (édité via le back‑office),
  initialisé par copie de la version publiée. **Aucun effet** sur le live.
- **Validation (`validated`)** : contrôles automatiques réussis (schéma des
  modules, intégrité référentielle **inter‑config**, exécution des **simulateurs**
  classification/prix/dialogue). Bloquant si échec.
- **Publication (`published`)** : le brouillon devient la version **active** ;
  ses données sont matérialisées dans les tables live (atomique) ; l'ancienne
  version passe `archived` (cible de rollback).
- **Rollback** : re‑publie une version `archived` (restaure son snapshot). En un
  clic.

---

## 4. Modèle de données

### 4.1 `config_modules` — **le registre** (clé de la généricité)
- **Rôle :** déclare **quelles tables** sont de la configuration versionnée.
- **Colonnes :** `key` (pk, ex. `catalog`, `questions`), `table_name` (unique),
  `natural_key` (colonne d'identité stable, ex. `slug`/`id`), `apply_order int`
  (ordre de dépendances), `schema jsonb?` (forme attendue pour validation
  data‑driven), `soft_delete_column?` (ex. `is_active`), `is_active`, `description`.
- **RLS :** admin. **💡** Ajouter un module = **insérer une ligne** ; le moteur
  n'est pas modifié.

### 4.2 `config_versions` — les versions
- **Colonnes :** `id`, `label`, `status config_version_status`, `notes?`,
  `parent_version_id?` (généalogie/rollback), `created_by`, `created_at`,
  `validated_by?`, `validated_at?`, `published_by?`, `published_at?`,
  `checksum?`, `metadata jsonb`.
- **Index :** un seul `published` actif (partial unique `where status='published'`).
- **RLS :** admin.

### 4.3 `config_snapshots` — le contenu (par module)
- **Rôle :** le **snapshot JSONB** d'un module pour une version.
- **Colonnes :** `id`, `version_id`, `module_key`, `payload jsonb` (tableau des
  lignes de la table de config), `row_count`, `created_at`.
- **Index :** `unique(version_id, module_key)`.
- **RLS :** admin.
- **💡** Agnostique du schéma → une nouvelle table de config est versionnable
  **sans migration** de ce système.

### 4.4 Enum
```
config_version_status = draft | validated | published | archived
```

---

## 5. Mécanique (fonctions serveur, génériques)

> Fonctions `SECURITY DEFINER` / Edge Functions **bornées au registre** (elles ne
> touchent **que** les tables déclarées `config_modules`).

- **`config_capture(version_id)`** : pour chaque module actif (ordre `apply_order`),
  sérialise les lignes de `table_name` → `config_snapshots.payload`.
- **`config_validate(version_id)`** : valide chaque `payload` contre
  `module.schema` (si fourni) + **intégrité référentielle inter‑config** (ex.
  `questions.set_id` existe dans le snapshot `question_sets`) + lance les
  **simulateurs** (classification, prix, dialogue). Renvoie un rapport ; passe la
  version en `validated` ou la laisse en `draft` avec erreurs.
- **`config_publish(version_id)`** : en **une transaction**, pour chaque module
  (ordre de dépendances) : **upsert par `natural_key`** des lignes du snapshot vers
  la table live, et **désactive** (soft‑delete via `soft_delete_column`) les lignes
  absentes du snapshot — **sans supprimer physiquement** (préserve les FK
  opérationnelles). Marque la version `published`, l'ancienne `archived`.
- **`config_rollback(target_version_id)`** : re‑publie le snapshot d'une version
  `archived` (même mécanique que publish). Un clic.

### 5.1 Où sont éditées les modifications du brouillon ?
- Le back‑office édite le **snapshot du brouillon** via des éditeurs **structurés**
  (mêmes UI relationnelles que l'admin : formulaire de questions, carte de zones,
  simulateur de prix…), qui écrivent dans `config_snapshots(payload)` de la version
  `draft`. Les **simulateurs** tournent sur le brouillon.
- Ainsi l'édition reste **isolée** du live (P : Brouillon), tout en gardant une
  **validation structurée** (via `module.schema`) — pas d'édition JSON « à la
  main ».
- *(Variante d'implémentation possible : un schéma `config_draft` miroir édité en
  relationnel, puis capturé. Choix d'implémentation ; l'architecture logique
  ci‑dessus reste la référence.)*

---

## 6. Garanties d'intégrité (points de conception clés)

- **PK/identité stables :** l'upsert se fait par `natural_key` (`slug`/`id`) →
  aucun ré‑identifiant → les `missions`/`payments` qui référencent une config
  restent valides après publication/rollback.
- **Suppression logique, pas physique :** retirer un service d'une version =
  `is_active=false` au live (jamais `DELETE`) → pas de FK cassée pour les missions
  historiques.
- **Application ordonnée + transactionnelle :** `apply_order` (ex. `question_sets`
  avant `questions` avant `question_options`) ; contraintes différables ; tout ou
  rien.
- **Config‑only :** le registre **refuse** toute table opérationnelle (liste
  interdite en dur côté fonction — garde‑fou structurel).
- **Idempotence** des publications/rollbacks (checksum de version).

---

## 7. Sécurité, audit & garde‑fous

- **Accès :** `admin` uniquement (RLS + rôle du claim). Publication/rollback =
  action sensible tracée (`audit_log` : version, auteur, diff résumé).
- **Non désactivable :** aucune version ne peut supprimer les garde‑fous
  structurels (P0 moteur de demandes, P1 contrôle humain, RLS, gate de paiement,
  effets de transition) — ils ne sont pas de la « configuration ».
- **Prévisualisation :** avant publication, diff **lisible** (ajouts/modifs/
  désactivations par module) + résultats des simulateurs.

---

## 8. Généricité prouvée (ajouter un module dans 1 an)

Pour rendre versionnable une **nouvelle** table de configuration (ex. demain
`dispatch_rules`, `promo_plans`, `moderation_rules`) :
1. Créer la table (migration **de cette feature**, pas du versionnement).
2. **Insérer une ligne** dans `config_modules` (`table_name`, `natural_key`,
   `apply_order`, `schema`, `soft_delete_column`).
3. **Fini** : capture, validation, publication et rollback la prennent en charge
   **automatiquement**. Aucun changement du moteur de versionnement.

---

## 9. Impacts modèle de données & API

- **Nouvelles tables :** `config_modules`, `config_versions`, `config_snapshots`
  (+ enum `config_version_status`). À intégrer dans `DATA_MODEL.md`.
- **Edge Functions / RPC :** `config-create-draft`, `config-validate`,
  `config-publish`, `config-rollback` (bornées au registre) — à ajouter dans
  `API_SPEC.md`.
- **ADMIN_PANEL :** module **AD‑26 Publications/rollback** (déjà prévu) devient le
  pilote de ce système ; chaque module de config gagne un **état** (au brouillon /
  publié) et un **diff**.
- **Registre initial (`config_modules`) :** seedé avec les tables du §1.

---

## 10. Cohérence & références

- Respecte P2 (tout data‑driven) et les garde‑fous P0/P1/RLS (non versionnables).
- Sépare strictement configuration et opérationnel (§1).
- Générique et extensible **sans refonte** (§8).
- Références : `Architecture_Technique.md`, `DATA_MODEL.md`, `ADMIN_PANEL.md`,
  `API_SPEC.md`.
