# ADMIN PANEL — Centre de pilotage — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Nature :** application **web** (back‑office). **Pas un CRUD** : un véritable
> **centre de pilotage** permettant de **faire évoluer la plateforme par la
> donnée**, sans toucher au code (P2). Chaque « métier » ou comportement nouveau
> s'ajoute ici.
>
> **Cohérence :** `PRD.md`, `SPEC_FONCTIONNELLE_V1.md`, `BUSINESS_RULES.md`,
> `DATA_MODEL.md`, `API_SPEC.md`, `UX_SPEC.md`, `CONVERSATION_ENGINE.md`,
> `Architecture_Technique.md`.

---

## 1. Philosophie

- **Piloter, pas seulement éditer.** Au‑delà du CRUD : **simulateurs**,
  **prévisualisation**, **publication/rollback**, **tests**, **observabilité**.
- **La donnée d'abord.** Tout ce qui change (taxonomie, classification, questions,
  workflows, transitions, règles, tarifs, textes, notifications, paramètres) est
  **administrable** → l'app s'adapte automatiquement.
- **Contrôle humain (P1).** L'admin/opérateur reste le décideur : la **file de
  revue** est au cœur du back‑office.
- **Sécurité & traçabilité.** Accès `admin` (RLS) ; **toute** action est
  journalisée (`audit_log`) ; les changements sensibles passent par un cycle
  **brouillon → prévisualisation → publication** avec **rollback**.

---

## 2. Navigation (modules) — écrans `AD‑xx`

| Module | Écran | Pilote |
|---|---|---|
| **Pilotage** | AD‑02 Tableau de bord | KPIs & santé |
| **Opérations** | AD‑03 Missions · AD‑04 Détail · **AD‑15 File de revue** | exécution + décision humaine |
| **Offre** | AD‑05 Taxonomie · AD‑16 Classification · AD‑17 Questions · AD‑18 Workflows · AD‑19 Transitions | le moteur de demandes |
| **Règles & prix** | AD‑06 Tarifs · AD‑20 Règles métier | monétisation & politiques |
| **Territoire** | AD‑07 Zones & horaires · AD‑12 Waitlist | couverture |
| **Contenu** | AD‑10 Notifications · AD‑21 Textes (i18n) · AD‑22 Modèles de conversation | ce que voit/lit l'utilisateur |
| **Configuration** | AD‑11 Paramètres (`app_config`) · AD‑23 Fonctionnalités (`feature.*`) | seuils & activation |
| **Personnes** | AD‑08 Utilisateurs · AD‑24 Opérateurs (vérification) | comptes & flotte |
| **Finance (sim)** | AD‑09 Litiges & remboursements simulés | résolution |
| **Gouvernance** | AD‑25 Journaux d'audit · AD‑26 Publications/rollback | traçabilité & versions |

---

## 3. Modules — détail

> Format : **rôle · ce qu'on gère · au‑delà du CRUD · tables · garde‑fous**.

### 3.1 AD‑02 Tableau de bord (statistiques)
- **Rôle :** vision temps réel de la plateforme.
- **Contenu :** missions par statut (dont **`pending_review` en attente**), délai
  médian de décision, taux d'acceptation/refus, complétion, écart prix estimé/réel,
  note moyenne, annulations par acteur, activité conversationnelle, charge équipe.
- **Au‑delà :** filtres période/zone/service ; export ; alertes (file de revue qui
  s'allonge, retards). Lecture sur **réplicas** pour ne pas charger la prod.
- **Tables :** agrégats sur `missions`, `mission_events`, `payments`, `ratings`,
  `conversations`.

### 3.2 AD‑15 File de revue (cœur — contrôle humain)
- **Rôle :** traiter les demandes `pending_review` (identique à OP‑04/05, aussi
  accessible en back‑office).
- **Contenu :** demande structurée + **transcript** de la conversation + plan
  proposé + suggestions IA + **tableau de bord dispatch** (dispo/charge/positions).
- **Actions :** **accepter / refuser / demander des infos** ; corriger la
  classification ; **fusionner/scinder** un plan multi‑services ; fixer le prix
  (`custom`).
- **Garde‑fous :** décision `[OP]/[ADMIN]` (P1) ; via `review-request` ; tracée.

### 3.3 AD‑03/04 Missions
- **Rôle :** superviser toute mission.
- **Contenu :** liste filtrable ; détail : **timeline** (`mission_events`),
  paiement (sim), preuves, chat, liens de groupe (multi‑services).
- **Au‑delà :** ré‑ouverture de litige, intervention (annulation/remboursement
  sim) avec motif tracé.

### 3.4 AD‑05 Taxonomie des services
- **Rôle :** gérer la **taxonomie interne** (`service_categories`) — **pas** un
  menu client (P0).
- **Contenu :** créer/modifier/**désactiver** un service ; famille, `base_fee`,
  `prep_buffer_min`, `legal_note`, `fulfillment`, `sort_order`, `metadata`.
- **Au‑delà (P7) :** une catégorie interne se définit comme une **combinaison de
  capacités** (`category_capabilities`) ; un **assistant** aide à mapper
  capacités → questions/workflow/tarifs. **Aucun** « métier » n'est requis pour
  traiter une demande (le moteur reste universel, P0) ; la catégorie sert le
  tarif/workflow/stats.
- **Tables :** `service_categories`, `category_capabilities`.

### 3.5 AD‑16 Capacités & classification (P7)
- **Rôle :** gérer les **capacités** (`capabilities`) — le vocabulaire du moteur —
  et apprendre au moteur à **comprendre** les besoins.
- **Contenu :** capacités (achat, livraison, diagnostic…) ; **indices**
  (`capability_classification` : mots‑clés, synonymes, exemples, regex, poids) ;
  **mapping catégorie ↔ capacités** (`category_capabilities`, pour tarif/workflow/
  stats) ; seuils (`app_config.classification.*`).
- **Au‑delà (centre de pilotage) :** **simulateur** — coller un texte (« mon pneu
  est crevé ») et voir les **capacités**/scores + catégorie dérivée ; **jeux de
  tests** (phrases attendues → capacités) pour non‑régression.
- **Tables :** `capabilities`, `capability_classification`, `category_capabilities`,
  `app_config`.

### 3.6 AD‑17 Questions dynamiques (éditeur de formulaire)
- **Rôle :** définir le **dialogue** de collecte, par service.
- **Contenu :** `question_sets`/`questions`/`question_options` ; type, ordre,
  `visible_when`/`required_when` (mini‑langage borné), `validation`, photos/docs ;
  textes via `content_strings`.
- **Au‑delà :** **éditeur visuel** (glisser‑déposer, conditions) ;
  **prévisualisation du dialogue** (simuler les réponses et voir l'enchaînement) ;
  duplication d'un set pour un nouveau service.
- **Tables :** moteur de questions.

### 3.7 AD‑18 Workflows
- **Rôle :** définir les **étapes** d'exécution par service (`category_workflow`).
- **Contenu :** activer/ordonner les étapes optionnelles (`shopping`,
  `preparing`, futures) ; marquer `requires_proof`.
- **Au‑delà :** visualisation du parcours résultant ; ajouter une **nouvelle
  étape** (déclare une valeur d'enum côté données + libellé) sans code.

### 3.8 AD‑19 Transitions (machine à états)
- **Rôle :** éditer les transitions autorisées (`mission_transitions`).
- **Contenu :** couples `(from, to)` + rôles autorisés + activation.
- **Au‑delà :** **visualisation du graphe** d'états ; garde‑fous : les **effets**
  (paiement, notifs) restent en code — l'éditeur n'ouvre pas des transitions sans
  effet défini (validation côté serveur).

### 3.9 AD‑06 Tarifs
- **Rôle :** monétisation entièrement en base.
- **Contenu :** `pricing_rules` (par zone) + `pricing_modifiers` (nuit/week‑end/
  férié/météo/urgence… par insertion, `condition` JSON).
- **Au‑delà :** **simulateur de prix** (service + distance + contexte → prix +
  ETA + détail) ; comparaison avant/après un changement de barème.
- **Tables :** `pricing_rules`, `pricing_modifiers`.

### 3.10 AD‑20 Règles métier
- **Rôle :** régler les **politiques** (`BUSINESS_RULES.md`) sans code.
- **Contenu :** seuils `app_config` (marge d'autorisation, tolérance de prix,
  délais injoignable/retard, fenêtre d'annulation, validité devis, TTL
  conversation…), interdits/restreints (activation de services).
- **Garde‑fous :** certaines règles (P1, RLS) sont **structurelles** et **non
  désactivables** (affichées en lecture seule avec mention « garanti par le code »).

### 3.11 AD‑07 Zones & horaires
- **Rôle :** couverture géographique.
- **Contenu :** `coverage_zones` (dessin de **polygone sur carte**),
  `service_windows` (créneaux par jour), activation.
- **Au‑delà :** **ajouter une ville** = dessiner une zone + horaires (aucun code) ;
  test « telle adresse est‑elle couverte / ouverte maintenant ? ».

### 3.12 AD‑11/23 Paramètres & fonctionnalités
- **Rôle :** `app_config` (source unique de configuration).
- **Contenu :** éditeur **typé** (booléen/nombre/chaîne/JSON) par clé, avec
  description et validation ; **flags `feature.*`** (activer/désactiver une
  fonctionnalité).
- **Au‑delà :** ciblage d'un flag (`rollout` : %/rôle/zone) ; historique des
  changements ; **rollback**.

### 3.13 AD‑21 Textes (i18n)
- **Rôle :** éditer **toute** copie affichée (`content_strings`).
- **Contenu :** recherche par clé/valeur, édition **par locale**, prévisualisation
  dans le contexte (écran/notification).
- **Au‑delà :** détection des clés manquantes par locale ; import/export.

### 3.14 AD‑10 Notifications
- **Rôle :** piloter la communication (`notification_templates` + `_triggers`).
- **Contenu :** modèles (audience, canal, titre/corps via `content_strings`),
  mapping **événement → template**, activation.
- **Au‑delà :** **prévisualisation** rendue (avec variables factices) ; **envoi de
  test** à un appareil ; activer/désactiver une notification sans code.

### 3.15 AD‑22 Modèles de conversation
- **Rôle :** régler le **comportement conversationnel** (formulations, ton,
  persona) et les paramètres du moteur.
- **Contenu :** gabarits de formulation (`content_strings` : questions,
  désambiguïsation, récapitulatif, messages d'impossibilité/waitlist) ; paramètres
  `app_config.conversation.*` (nb max de questions, tentatives de désambiguïsation,
  tours de contexte, TTL) ; **prompts/guides IA** versionnés (bornés).
- **Au‑delà :** **bac à sable de dialogue** (rejouer une conversation avec les
  réglages courants) ; A/B de formulations.

### 3.16 AD‑08/24 Utilisateurs & opérateurs
- **Utilisateurs :** rechercher/voir un `profiles` ; gérer le **rôle** (garde‑fou
  anti‑escalade) ; actions RGPD (export, suppression).
- **Opérateurs :** `operator_profiles` — **vérification** (`is_verified`,
  `documents`), véhicule, disponibilité, gains/avances (sim).

### 3.17 AD‑09 Litiges & remboursements simulés
- **Rôle :** résoudre les `disputes`.
- **Contenu :** dossier (preuves agrégées, chat, montants) ; **remboursement
  simulé** (total/partiel) via `refund`, motif tracé ; clôture.
- **Garde‑fous :** remboursement exceptionnel = `[ADMIN]` ; idempotent.

### 3.18 AD‑25/26 Audit & publications
- **Audit :** `audit_log` — qui a changé quoi, quand, diff. Filtrable.
- **Publications/rollback :** pilote le **versionnement de toute la configuration
  métier** (cf. **`CONFIG_VERSIONING.md`**) : cycle **Brouillon → Validation →
  Publication → Rollback** en un clic, générique (registre `config_modules`),
  avec diff lisible et simulateurs avant publication. Une version couvre
  taxonomie, classification, questions, workflows, transitions, règles, tarifs,
  zones, horaires, paramètres, notifications, templates de conversation, contenus,
  et tout futur module — **jamais** les données opérationnelles.

---

## 4. Sécurité & gouvernance

- **Accès `admin`** (RLS) ; opérations d'écriture de configuration réservées.
- **Journalisation systématique** (`audit_log`) de toute action admin.
- **Garde‑fous non désactivables** : contrôle humain (P1), RLS, gate de paiement,
  effets de transition — affichés mais **verrouillés** (« garanti par le code »).
- **Validation serveur** de toute configuration (types, cohérence, conditions
  bornées) avant publication.
- **Environnements** : configuration testable en `staging` avant `prod`.

---

## 5. Ce qui pourra devenir administrable (prospective — minimiser le code)

> Prévu pour être ajouté **sans refonte** (mécanismes déjà data‑driven) :

- **Versionnement de configuration** (table de versions + publication/rollback
  généralisés à toutes les tables de règles).
- **Ciblage & A/B** via `feature.*` (`rollout` : %/rôle/zone/date) et A/B de
  formulations/tarifs.
- **Permissions granulaires (RBAC data‑driven)** : rôles/permissions en base
  au‑delà des 3 rôles actuels (ex. `dispatcher`, `support`), sans code.
- **Éditeurs visuels** : workflow (graphe), questions (formulaire), zones (carte).
- **Simulateurs** : classification, prix, **dialogue** — déjà prévus (AD‑16/06/22).
- **Partenaires** (`fulfillment='partner'`) : annuaire, règles de mise en relation.
- **Dispatch multi‑intervenant** : règles d'affectation (proximité, charge,
  priorité, compétences) en données.
- **Plans tarifaires / promotions** : `promo_codes` (V2), abonnements, SLA.
- **Modération** : règles de filtrage (chat/conversation) éditables.
- **Intégrations/webhooks sortants** : déclencheurs configurables.
- **Segments & analytics** : tableaux de bord configurables, exports planifiés.
- **Templates de missions** : demandes pré‑remplies récurrentes.

> Chacun réutilise les tables/mécanismes existants (`app_config`,
> `content_strings`, moteurs de règles) ou une petite table dédiée — **jamais** une
> réécriture de l'app.

---

## 6. Impacts modèle de données

- **Aucune nouvelle table indispensable** en V1 : le back‑office **édite les
  tables existantes** (référentiel, config, contenu, règles) sous RLS admin.
- **Versionnement de configuration** (validé) : système générique
  `config_modules` / `config_versions` / `config_snapshots` — cf.
  **`CONFIG_VERSIONING.md`** (acté dans `DATA_MODEL.md`).
- **`audit_log`** (déjà prévu) couvre la traçabilité.
- **RBAC granulaire** (futur) : tables `roles`/`permissions` — **non V1**.

---

## 7. Cohérence & références

- Chaque module **édite des données** déjà définies dans `DATA_MODEL.md` ; les
  actions passent par PostgREST (RLS admin) ou des Edge Functions
  (`review-request`, `refund`, `send-push` de test) — `API_SPEC.md`.
- La **file de revue** applique **P1** ; la **taxonomie** applique **P0** ; les
  **simulateurs** rendent le pilotage sûr (tester avant publier).
- Références : tous les documents `docs/`. À venir : `GPS_TRACKING.md`,
  `NOTIFICATIONS.md`, `CHAT.md`.
