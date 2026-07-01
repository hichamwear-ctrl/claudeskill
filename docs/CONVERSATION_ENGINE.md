# CONVERSATION ENGINE — Moteur conversationnel — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Rôle :** décrire le **cœur du produit** : un moteur de **conversation piloté
> par les données** qui guide l'utilisateur, en langage naturel, jusqu'à une
> demande **complète**, puis la présente à l'opérateur pour décision.
>
> **Deux principes surplombent tout ce document :**
> - **P0 — moteur UNIVERSEL de traitement de demandes :** pas de catalogue exposé.
>   Le moteur doit traiter **n'importe quelle** demande — **même inédite, jamais
>   vue auparavant** — sans qu'on ait à « ajouter un service ». La taxonomie est
>   **100 % interne** (classification, workflow, tarif, stats, affectation, règles)
>   et **jamais montrée au client**. Elle **optimise** le traitement ; elle n'est
>   **jamais une condition** pour accepter une demande. On enrichit *règles,
>   questions, classification* — **jamais l'architecture** pour un « métier ».
> - **P1 — contrôle humain :** l'IA **prépare**, l'opérateur **décide**. L'IA ne
>   crée ni ne valide jamais une mission ; elle ne déclenche aucun paiement.
>
> **Cohérence :** `PRD.md`, `BUSINESS_RULES.md`, `SPEC_FONCTIONNELLE_V1.md`,
> `DATA_MODEL.md`, `API_SPEC.md`.

---

## 1. Philosophie de conception

- **Ce n'est pas un formulaire dynamique.** C'est un **dialogue** : une question à
  la fois, des relances naturelles, une adaptation à chaque réponse, un retour en
  arrière possible, une construction **progressive**.
- **Déterministe sur des données, assisté par l'IA.** Le *déroulé* (quelle
  information manque, quelle question poser) est calculé par un **moteur
  déterministe** à partir de **tables** (intentions, slots, conditions). L'IA
  intervient sur les tâches **linguistiques** (comprendre, extraire, reformuler,
  proposer) — bornée, jamais décisionnaire.
- **Pourquoi ce partage ?** Robustesse, testabilité, coût maîtrisé, et surtout :
  **on fait évoluer le comportement en éditant des données**, pas en réécrivant
  des prompts ou du code. L'IA peut être remplacée/améliorée sans toucher au flux.

### 1.1 Frontière IA / moteur / opérateur

| Tâche | Qui | Nature |
|---|---|---|
| Détecter la/les **intention(s)** depuis le texte libre | IA (guidée par données) | **proposition** |
| Extraire des **valeurs de slots** depuis une réponse en langage naturel | IA | **proposition** (revalidée) |
| Choisir **la prochaine question** | **Moteur (déterministe)** | décision technique bornée |
| **Reformuler** naturellement une question | IA (templates + `content_strings`) | rendu |
| Détecter un **changement de contexte** | IA + moteur | proposition + recalcul |
| Proposer un **découpage multi‑services** | IA | **proposition** |
| **Valider** les réponses (types, obligation, cohérence) | **Moteur (serveur)** | déterministe |
| **Accepter / refuser / demander plus** | **Opérateur** | **décision humaine** |

---

## 2. Vue d'ensemble du pipeline

```
1. INTAKE        texte libre (+ voix/photo)               → conversation ouverte (draft)
2. INTENT        classification → 1..N intentions candidates (scores)
3. PLAN          intentions → plan de mission(s) proposé (mono ou multi‑service)
4. SLOT-FILLING  boucle : détecter info manquante → poser 1 question → extraire → valider
5. CONTEXT       si une réponse change tout → re‑classer, ajuster le plan, revenir en arrière
6. SUMMARY       récapitulatif complet généré
7. SUBMIT        transition created → pending_review        → l'IA S'ARRÊTE ICI
8. REVIEW        l'opérateur voit transcript + demande structurée + suggestions IA → DÉCIDE
```

L'IA agit des étapes 2 à 6 (assistance). L'étape 7 est un **garde‑fou** : au‑delà,
plus aucune automatisation — **P1**.

---

## 3. Modèle de données du moteur (piloté par la donnée)

> Nouvelles tables (à consolider dans `DATA_MODEL.md`). Elles s'appuient sur les
> mécanismes existants : `service_categories` (taxonomie/intentions),
> `category_classification` (indices), moteur de questions
> (`question_sets/questions/question_options`), `content_strings` (formulations),
> `app_config` (modèle IA, seuils).

### 3.1 `conversations`
- **Rôle :** session de dialogue d'un client ; **contient l'état** (source de
  reprise et de contexte).
- **Colonnes :** `id`, `client_id`, `status ('active'|'submitted'|'abandoned'|'expired')`,
  `state jsonb` (slots remplis, position, intents retenus), `plan jsonb`
  (mission(s) proposée(s)), `detected_intents jsonb`, `locale`, `created_at`,
  `updated_at`, `expires_at`, `metadata jsonb`.
- **Relations :** N‑1 `profiles` ; 1‑N `conversation_turns` ; 1‑N `missions`
  (une conversation peut produire **plusieurs** missions — §7).
- **RLS :** propriétaire (client) + opérateur/admin en lecture pour la revue.

### 3.2 `conversation_turns`
- **Rôle :** historique **immuable** des tours (contexte + audit).
- **Colonnes :** `id`, `conversation_id`, `role ('user'|'assistant'|'system')`,
  `content text`, `media jsonb?` (chemins Storage), `intent_ref?`,
  `slot_key?` (question adressée), `extracted jsonb?` (valeurs proposées par l'IA),
  `created_at`.
- **RLS :** participants de la conversation + admin.

### 3.3 Intentions & slots (réutilisation)
- **Intention** = une `service_categories` (taxonomie) atteignable par
  classification. Une conversation peut porter **plusieurs** intentions.
- **Slot** = une `questions` d'un `question_set` rattaché à la catégorie
  (`required_when`, `visible_when`, `validation`, `type`). Les **valeurs** vont
  dans `conversations.state` puis, à la soumission, dans `missions.details`.
- **💡 Aucune nouvelle notion de « slot » n'est nécessaire** : le moteur de
  questions **est** le schéma de slots. On évite une table dédiée.

### 3.4 Liens missions (multi‑services)
- `missions.conversation_id` (origine), `missions.group_id?` (regroupe les
  missions d'une même demande), `missions.sequence?` (ordre),
  `missions.depends_on_mission_id?` (dépendance : B après A).
- **💡** Pas de table « group » séparée en V1 : `group_id` (uuid partagé) +
  `sequence`/`depends_on` suffisent. Une table `mission_groups` pourra être
  ajoutée si un jour on attache des données au groupe.

---

## 4. Gestion des intentions

- **BR‑CE‑01 [AUTO/IA] Détection :** à l'intake, `classify-request` renvoie
  `1..N` intentions candidates avec score (IA guidée par `category_classification`
  + règles). 
- **BR‑CE‑02 Confiance :** si `score ≥ app_config.classification.min_confidence`
  et une seule intention nette → on la retient. Sinon → **désambiguïsation** (§8)
  ou **multi‑intention** (§7).
- **BR‑CE‑03 Re‑détection :** à chaque tour, si le texte introduit une intention
  **nouvelle** ou **contradictoire**, le moteur relance la détection (§5).
- **BR‑CE‑04 [P1] :** l'intention retenue est **provisoire** ; l'opérateur peut la
  **corriger** en revue (re‑classification humaine).
- **BR‑CE‑05 Intention GÉNÉRIQUE (universalité) :** si **aucune** catégorie ne
  correspond (demande inédite), la conversation **ne s'arrête pas**. Le moteur
  bascule sur un **`question_set` générique** (questions universelles : quoi,
  où, quand, précisions, photos/documents éventuels) et construit un dossier
  complet. La mission est marquée `category_id = null` (+ `metadata.classification
  = unknown`) ; **l'opérateur classe/tarifie à la revue**. Une catégorie n'est
  **jamais** requise pour accepter une demande — elle ne fait qu'**améliorer** le
  questionnaire/tarif quand elle existe.

---

## 5. Boucle de questions dynamiques (le cœur)

### 5.1 Politique déterministe « prochaine question »
À chaque tour, le **moteur** (pas l'IA) calcule :
```
slots = questions des intentions retenues (ordonnées par sort_order)
pending = slots où required_when(state)=vrai ET visible_when(state)=vrai ET valeur absente/invalide
next = premier pending
si next existe        → poser next (formulée par l'IA)
sinon                 → proposer le RÉCAPITULATIF (§ SUMMARY)
```
- **Une seule question à la fois** (BR‑CE‑10).
- **Conditions** évaluées via le **mini‑langage borné** (`DATA_MODEL` §12) — donc
  « chaque réponse influence les questions suivantes » **sans code**.
- **Slots optionnels** ignorés s'ils n'apportent rien ; on ne sur‑questionne pas.

### 5.2 Rôle de l'IA dans la boucle
- **Formulation :** transformer la question (template `content_strings`) en phrase
  naturelle, contextualisée (ex. reprendre l'enseigne déjà citée).
- **Extraction :** depuis la réponse libre, proposer les **valeurs** des slots
  (`extracted jsonb`), y compris **plusieurs slots d'un coup** si l'utilisateur
  en dit plus (« du lait demi‑écrémé, 2 briques, chez Carrefour »).
- **Garde‑fou :** toute valeur extraite est **revalidée** par le moteur
  (`validation`, type, options) ; en cas de doute → question de **confirmation**,
  jamais d'invention.

### 5.3 Demandes de photos / documents
- Un slot de `type = photo|document` déclenche une invitation à joindre un média
  (upload Storage) ; l'IA peut **suggérer** l'utilité (« une photo du pneu
  aiderait »). Obligatoire/optionnel piloté par `required_when`.

### 5.4 Exemples (illustratifs — tout vient des données)
```
« J'ai oublié du lait »   → intention: groceries
  slots: enseigne? quantité? liste existante? autres articles? adresse? créneau?
« Mon pneu est crevé »    → intention: car_assist
  slots: véhicule? roulable(bool)? position? photo? roue de secours(bool)?
        (si roulable=false → slot « nécessite remorquage » → HORS PÉRIMÈTRE → §10)
```

---

## 6. Détection des informations manquantes
- **BR‑CE‑20 [AUTO] :** « manquant » = slot `required_when(state)=vrai` sans valeur
  **valide**. La complétude d'une intention = aucun slot requis manquant.
- **BR‑CE‑21 :** le récapitulatif n'est proposé que lorsque **toutes** les
  intentions retenues sont complètes (ou marquées optionnelles/skippées).
- **BR‑CE‑22 :** un slot peut devenir requis **a posteriori** (une réponse active
  `required_when` d'un autre) → la boucle le rattrape automatiquement.

---

## 7. Demandes multi‑services

Une conversation peut détecter **plusieurs intentions**. Trois stratégies, **le
moteur propose, l'opérateur tranche si ambigu** :

| Cas | Stratégie proposée | Modèle |
|---|---|---|
| Services **indépendants** (« un plombier **et** des courses ») | **Découpage en missions** | N `missions`, même `group_id`, sans dépendance |
| Services **enchaînés** (« acheter des médicaments **puis** les déposer chez ma mère ») | **Mission composée / enchaînée** | soit 1 mission (achat + dropoff distinct), soit 2 missions `depends_on`/`sequence` |
| **Ambigu** (découpage incertain) | **Escalade opérateur** | plan marqué `needs_operator_split=true` |

- **BR‑CE‑30 [IA] :** l'IA propose un **plan** (`conversations.plan`) : liste de
  missions candidates (intention + slots + ordre/dépendances).
- **BR‑CE‑31 :** le client **confirme** le découpage proposé (formulé
  naturellement : « Je vois deux choses : … et … . C'est bien ça ? »).
- **BR‑CE‑32 [P1] :** à la revue, l'opérateur peut **fusionner, scinder,
  réordonner** ou refuser tout ou partie du plan. La décision reste **humaine**.
- **BR‑CE‑33 :** chaque mission du groupe suit **sa propre** machine à états
  (chacune peut être acceptée/refusée indépendamment), mais reste **liée**
  (`group_id`) pour une vision d'ensemble.

---

## 8. Demandes ambiguës
- **BR‑CE‑40 :** ambiguïté d'**intention** (score bas / plusieurs proches) →
  question de **désambiguïsation** ciblée (« S'agit‑il plutôt de *récupérer* un
  colis ou de *le faire livrer* ? »), bornée à quelques options (les candidats).
- **BR‑CE‑41 :** ambiguïté de **découpage** → §7 (escalade opérateur).
- **BR‑CE‑42 :** après N tentatives de désambiguïsation (config), **soumettre tel
  quel** à l'opérateur avec la mention d'ambiguïté plutôt que de bloquer le client.

---

## 9. Demandes hors périmètre (≠ demande non reconnue)

> **Important (P0) :** une demande **non reconnue** n'est **jamais** « impossible » —
> elle est traitée par le **parcours générique** (BR‑CE‑05) et envoyée à
> l'opérateur. « Hors périmètre » ne concerne **que** l'illégal/interdit ou
> l'indisponibilité géographique.

- **BR‑CE‑50 :** seul un slot révélant un **interdit** (illégal, dangereux,
  remorquage, médicaments sur ordonnance… `BUSINESS_RULES` §3) déclenche une
  explication **avec tact** + alternative éventuelle. **L'absence de catégorie
  n'en fait pas partie** (→ parcours générique).
- **BR‑CE‑51 [P1] :** l'IA **ne refuse jamais définitivement** de sa propre
  autorité une demande recevable ; en cas de doute, elle **laisse l'opérateur
  décider** (soumission avec drapeau). Le « refus » ferme est une décision
  **opérateur** (`rejected`).
- **BR‑CE‑52 :** hors zone/horaires détecté tôt (`zone-check`) → proposé avant de
  poursuivre le questionnaire (éviter un effort inutile) ; sinon inscription
  `waitlist`.

---

## 10. Interactions IA ↔ Opérateur

Ce que l'IA **prépare** et transmet à la revue (écran OP‑05) :
- le **transcript** complet (`conversation_turns`),
- la **demande structurée** (intentions, slots remplis, médias, plan),
- des **suggestions** : classification proposée (+ alternatives), découpage
  proposé, prix estimatif, signaux (ambiguïté, contrainte, matériel nécessaire),
- une **check‑list de faisabilité** (dispo équipe, zone, horaires, complexité).

Ce que l'opérateur **décide** (inchangé, P1) : accepter / refuser / demander plus ;
corriger la classification ; fusionner/scinder le plan ; fixer le prix (`custom`).

- **BR‑CE‑60 :** l'IA peut **assister l'opérateur** aussi (résumé, question
  suggérée à poser au client), mais **n'exécute** aucune transition.

---

## 11. Reprise d'une conversation interrompue
- **BR‑CE‑70 :** l'état vit en base (`conversations.state`), la conversation est
  **reprenable** à tout moment (fermeture d'app, réseau) via deep‑link — on
  **repose la même question** en cours, contexte intact.
- **BR‑CE‑71 :** une conversation inactive au‑delà de
  `app_config.conversation.ttl_hours` passe `expired` (purge `pg_cron`) ; un
  brouillon `missions.status='created'` non soumis suit la même logique.
- **BR‑CE‑72 :** `needs_information` (revue) **rouvre** la conversation existante
  avec les nouvelles questions de l'opérateur — même canal, contexte conservé.

## 12. Conservation du contexte
- **BR‑CE‑80 :** `conversations.state` = **vérité structurée** (slots, intentions,
  position, plan) ; `conversation_turns` = **historique** (audit + reformulations).
- **BR‑CE‑81 :** l'IA reçoit à chaque tour un **contexte borné** (état structuré +
  N derniers tours), pas tout l'historique brut → coût/latence maîtrisés,
  comportement reproductible.
- **BR‑CE‑82 :** aucune info déjà connue n'est redemandée (le moteur saute les
  slots déjà remplis et valides).

## 13. Changements de contexte (retour en arrière)
- **BR‑CE‑90 :** si une réponse **contredit** un slot déjà rempli ou **change
  l'intention** (« finalement ce n'est pas une fuite, c'est un radiateur à
  purger »), le moteur : re‑classe → recalcule le plan → **conserve les slots
  compatibles** → invalide/repose les slots devenus incohérents.
- **BR‑CE‑91 :** chaque bascule est tracée (`conversation_turns`, `state` versionné)
  pour audit et pour permettre un « annuler ».

## 14. Règles d'un parcours naturel (UX conversationnelle)
- une question à la fois ; **accuser réception** de la réponse ; **ne jamais
  redemander** ; **reformuler** avec les mots de l'utilisateur ; proposer des
  **raccourcis** (boutons rapides pour `select`) ; **borne** le nombre de
  questions (config) et proposer « autre chose ? » avant de conclure ;
  **récapituler** avant soumission ; ton défini par `content_strings` (éditable).
- **BR‑CE‑100 :** le client peut toujours **écrire librement** (pas seulement
  répondre) — le moteur ré‑extrait et se réaligne.

## 15. Ce qui est **donnée** vs **code**

| Élément | Piloté par |
|---|---|
| Intentions (taxonomie) & indices | `service_categories`, `category_classification` |
| Slots, ordre, conditions, obligation, validation, photos/docs | moteur de questions |
| Formulations, ton, désambiguïsation, récap | `content_strings` (templates) |
| Modèle IA, seuils, bornes, TTL, nb max de questions | `app_config` (`classification.*`, `conversation.*`) |
| Politique « prochaine question », validation serveur, garde‑fous P1 | **code** (déterministe, testé) |
| Découpage multi‑services (proposition) | IA ; **décision** opérateur |

> Ajouter/ajuster un métier, une question, une règle de branchement, une
> formulation = **édition de données** (admin), **sans redéploiement**.

## 16. Sécurité & garde‑fous
- **P1 absolu :** l'IA ne franchit jamais `pending_review` ; ne crée pas de
  paiement ; ne rejette pas définitivement.
- **Anti‑hallucination :** toute valeur extraite est **revalidée** ; les options
  d'un `select` sont **fermées** (l'IA choisit parmi `question_options`, n'invente
  pas) ; en cas de doute → confirmation.
- **Coût/abus :** `classify-request`/extraction soumis à **rate‑limit**
  (`app_config`) ; contexte borné.
- **Confidentialité :** modération (anti‑coordonnées) et RGPD comme le chat
  (`CHAT.md`) ; le transcript suit la rétention configurée.
- **Déterminisme testable :** la politique de dialogue (sans IA) est
  **rejouable** → tests automatisés du flux indépendamment du modèle.

## 17. Impacts modèle de données (à consolider dans `DATA_MODEL.md`)
- **Nouvelles tables :** `conversations`, `conversation_turns`.
- **`missions` :** ajouter `conversation_id`, `group_id?`, `sequence?`,
  `depends_on_mission_id?`.
- **`app_config` :** clés `classification.*` (min_confidence, model, max_candidates),
  `conversation.*` (ttl_hours, max_questions, max_disambiguation, context_turns).
- **Réutilisé sans nouvelle table :** questions (=slots), `category_classification`,
  `content_strings`, `service_categories`.
- **Edge Functions :** `classify-request` (intentions), `converse` (tour de
  dialogue : extraction + prochaine question), `submit-request` (clôture →
  `pending_review`). `converse` orchestre IA + moteur déterministe.

## 18. Cohérence & références
- Aligné avec **P0** (moteur de demandes) et **P1** (contrôle humain) ; s'arrête à
  `pending_review` ; réutilise le moteur de questions et la classification.
- Ajouts (`conversations`, `conversation_turns`, colonnes de liaison `missions`,
  clés `app_config`, Edge `converse`) : **extensions** cohérentes, à intégrer dans
  `DATA_MODEL.md` et `API_SPEC.md`.
- Références : `PRD.md`, `BUSINESS_RULES.md`, `SPEC_FONCTIONNELLE_V1.md`,
  `DATA_MODEL.md`, `API_SPEC.md`, `UX_SPEC.md`, `NOTIFICATIONS.md`, `CHAT.md`.
