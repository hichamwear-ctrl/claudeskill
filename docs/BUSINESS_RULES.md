# BUSINESS RULES — Règles métier — `[NOM_PRODUIT]` (V1)

> **Version :** 1.0 · **Statut :** proposition à valider
> **Rôle :** référence **unique et exhaustive** des règles métier de la V1.
> Toute logique applicative (Edge Functions, `transition_mission`, RLS, UI) doit
> s'y conformer. Les valeurs chiffrées sont **en base** (`app_config`,
> `pricing_rules`, `service_categories`) — jamais codées en dur.
>
> **Cohérence :** aligné avec `PRD.md`, `SPEC_FONCTIONNELLE_V1.md`,
> `UX_SPEC.md`, `Architecture_Technique.md`. Priorité en cas de divergence :
> PRD (intention) > BUSINESS_RULES (règle métier) > SPEC/UX (déclinaison) ;
> l'architecture prime sur le technique.

---

## 0. Conventions

### 0.1 Propriété de décision

| Tag | Signification |
|---|---|
| `[AUTO]` | Décision **automatique** (système / Edge Function / trigger / cron). Déterministe, sans jugement. |
| `[OP]` | Décision **opérateur** (rôle `operator`, ou `admin`). Jugement humain. |
| `[ADMIN]` | Décision **administrateur** (rôle `admin`). Exploitation, exceptions, litiges. |

> **Principe P1 (contrôle humain) :** aucune **acceptation** de mission ni aucun
> **paiement** n'est `[AUTO]`. L'acceptation est toujours `[OP]`.

### 0.2 États de mission référencés

`created → pending_review → {accepted | rejected | needs_information}` puis
`accepted → assigned → [shopping] → [preparing] → en_route → arrived →
in_progress → completed → rated`. Transverses : `cancelled`, `failed`.
(`searching` réservé au dispatch multi‑intervenant — hors V1.)

### 0.3 Paramètres de configuration utilisés (`app_config`)

| Clé | Rôle | Valeur démo |
|---|---|---|
| `quote_validity_hours` | validité du prix proposé (custom) | 24 |
| `nearby_radius_m` | seuil « intervenant proche » | 500 |
| `delay_grace_min` | tolérance avant « en retard » | 10 |
| `night_window` | plage nuit (supplément) | `{"from":"22:00","to":"06:00"}` |
| `max_concurrent_missions` | charge max par intervenant | 1 (V1) |
| `price_tolerance_pct` | écart prix toléré sans réaccord client | 20 |
| `unreachable_timeout_min` | délai avant « client injoignable » | 10 |
| `payment_authorization_ttl_min` | durée de vie d'une autorisation sim | 60 |
| `dispute_window_hours` | fenêtre d'ouverture d'un litige après clôture | 72 |
| `cancellation_free_window_min` | annulation client sans frais après acceptation | 5 |

> Ces clés étendent `app_config` (créée en M1.3). Ajouter un seuil = insérer une
> ligne, **sans code**.

---

## 1. Gouvernance des décisions (vue d'ensemble)

| Domaine | `[AUTO]` | `[OP]` | `[ADMIN]` |
|---|---|---|---|
| Zone & horaires | vérification (`zone-check`) | — | définition des zones/créneaux |
| Estimation de prix | calcul (`estimate-price`) | fixe le prix d'une demande libre à l'acceptation | barème (`pricing_rules`/`modifiers`) |
| **Acceptation / refus / demande d'infos** | — | **décision** | peut décider aussi |
| Affectation intervenant | auto après paiement (V1) | (multi‑op : dispatch) | règles de dispatch |
| Transitions d'exécution | validation (allow‑list) | déclenche chaque étape | — |
| Paiement sim (autoriser/capturer/annuler/rembourser) | exécution mécanique | déclenche à la clôture / annulation | remboursement exceptionnel, litige |
| Retard | détection + notif | action proactive (message) | compensation (sim) |
| Litige | agrégation des preuves | signalement | **arbitrage & remboursement** |
| Catalogue / config / rôles | — | — | gestion complète |

---

## 2. Validation opérateur (cœur du contrôle humain)

### 2.1 Éléments visibles avant décision `[OP]` (écran OP‑05)

L'opérateur voit **l'intégralité** de la demande **et** le contexte d'exploitation :

| Bloc | Contenu |
|---|---|
| Demande | besoin exprimé, réponses aux questions, **photos**, articles/quantités, remarques |
| Localisation | adresse(s) (retrait/livraison), complétude, distance, présence en zone |
| Tarif | prix estimatif + détail (`PriceBreakdown`), ETA ; **advance_estimate** si applicable |
| Client | prénom, historique succinct (nb missions, note moyenne), signaux de risque éventuels |
| **Équipe** | disponibilité (Presence/statut), **charge** (missions actives), **missions en cours**, **localisation des intervenants** (carte) |
| Contraintes | catégorie active ? dans les horaires ? mentions légales de la catégorie |

- **BR‑001 `[AUTO]`** : à l'ouverture d'OP‑05, le système recharge zone/horaires
  et recalcule l'estimation, pour éviter une décision sur une donnée périmée.
- **BR‑002 `[OP]` Prise en charge (claim) :** avant de décider, l'opérateur
  **claime** la demande (`review-claim`, verrou atomique). Tant qu'une demande
  n'est pas claimée, la file n'expose qu'un **résumé** ; le **détail complet**
  (texte libre, transcript) n'est visible **qu'après claim** (vie privée). Un
  autre opérateur ne peut pas la traiter en parallèle. Claim expiré
  (`app_config.review.claim_ttl_min`) → remis en file. `[ADMIN]` peut réassigner.

### 2.2 Critères d'ACCEPTATION `[OP]`

Une demande **peut** être acceptée si **tous** les critères sont réunis :

- **BR‑010** la catégorie est **active** (`service_categories.is_active`) ;
- **BR‑011** l'adresse est **complète et géocodable**, en **zone** couverte ;
- **BR‑012** la demande est **dans les horaires** de service (ou planifiable) ;
- **BR‑013** au moins **un intervenant est disponible** (critères §2.5) ;
- **BR‑014** la demande est **licite** et **dans le périmètre** du catalogue (§3) ;
- **BR‑015** le besoin est **suffisamment clair** pour être réalisé sans risque ;
- **BR‑016** pour une **demande libre** (`custom`), l'opérateur **fixe un prix**
  et un ETA (devis, validité `quote_validity_hours`) ;
- **BR‑017** l'estimation n'est pas manifestement erronée (sinon §6).

Effet `[OP]` : `pending_review → accepted` ; `reviewed_at`, `reviewed_by` posés ;
notif `request_accepted` ; **paiement débloqué** (jamais avant).

### 2.3 Critères de REFUS `[OP]`

Une demande **doit** être refusée si l'un des cas suivants s'applique :

- **BR‑020** produit/service **interdit** ou **hors catalogue** (§3) ;
- **BR‑021** demande **illicite**, dangereuse, ou contraire aux mentions légales ;
- **BR‑022** **hors zone/horaires** sans créneau réalisable ;
- **BR‑023** **aucun intervenant** ne peut raisonnablement réaliser la mission ;
- **BR‑024** demande **abusive / frauduleuse** ou manifestement de test malveillant ;
- **BR‑025** adresse **impossible**, inaccessible ou **non sécurisée** ;
- **BR‑026** le client **ne fournit pas** les informations indispensables après
  une demande d'informations (§2.4) — refus après relance restée sans réponse.

Effet `[OP]` : `pending_review → rejected` ; `review_reason` obligatoire ; notif
`request_rejected` (avec motif lisible). **Terminal.** Aucun paiement n'a eu lieu.

### 2.4 Critères de DEMANDE D'INFORMATIONS `[OP]`

À utiliser quand la demande est **récupérable** mais incomplète/ambiguë :

- **BR‑030** besoin **ambigu** (quantité, marque, taille, précision manquante) ;
- **BR‑031** **adresse incomplète** mais corrigeable (étage, digicode, accès) ;
- **BR‑032** **photo** ou justificatif nécessaire (ex. pièce à identifier) ;
- **BR‑033** **budget / avance de frais** à préciser (courses/pharmacie) ;
- **BR‑034** fenêtre horaire / disponibilité du client à confirmer.

Effet `[OP]` : `pending_review → needs_information` ; `review_reason` = question(s) ;
notif `request_needs_info` ; **la conversation est rouverte**. Le client répond
(chat) puis **re‑soumet** (`needs_information → pending_review`).

- **BR‑035 `[AUTO]`** : une demande restée en `needs_information` au‑delà d'un
  délai (config, ex. 48 h) peut être **auto‑annulée** (`cancelled`, acteur
  `system`) après notification — libère la file. *(Valeur à confirmer.)*

### 2.5 Critères de DISPONIBILITÉ de l'équipe

Un intervenant est **disponible** pour une nouvelle mission si **tout** est vrai :

- **BR‑040** `operator_profiles.status = 'available'` **et** présent en ligne
  (Realtime **Presence**) ;
- **BR‑041** **charge** actuelle `< max_concurrent_missions` (V1 = 1) ;
- **BR‑042** l'heure courante est **dans un `service_window`** actif de la zone ;
- **BR‑043** (multi‑op) l'intervenant est **assez proche** / peut atteindre
  l'adresse dans un ETA raisonnable.

- **BR‑044 `[AUTO]`** : le calcul de disponibilité/charge est fourni à l'écran de
  revue en lecture ; il **n'affecte** pas automatiquement — la décision reste `[OP]`.
- **BR‑045 `[OP]`** : l'opérateur peut **accepter malgré** une charge pleine
  (mission planifiée) ; il en assume la conséquence (file d'exécution).

---

## 3. Demandes, produits & services interdits

- **BR‑050 `[ADMIN]`** définit le catalogue autorisé ; hors catalogue = refusable.
- **BR‑051** **Interdits absolus** (refus `[OP]` systématique) :
  médicaments **sur ordonnance** ; armes, explosifs, produits dangereux ;
  stupéfiants ; produits illicites ; **remorquage** de véhicule (hors périmètre
  `car_assist`) ; transport de personnes ; espèces/valeurs ; animaux vivants ;
  tout ce qui contrevient à la loi locale.
- **BR‑052** **Restreints** (acceptation conditionnée, mention légale) : pharmacie
  **sans ordonnance uniquement** (`legal_note`) ; alcool/tabac soumis aux règles
  d'âge (contrôle à la remise) — *à activer/désactiver via `is_active`/`app_config`*.
- **BR‑053 `[ADMIN]`** peut **désactiver** une catégorie à tout moment
  (`is_active = false`) pour arbitrage légal, sans redéploiement.

---

## 4. Cas d'exploitation (couverture exhaustive)

### 4.1 Demande irréalisable (avant acceptation)
- **BR‑060 `[OP]`** : si irréalisable dès la revue → **refus** (§2.3) avec motif.
- **BR‑061 `[OP]`** : si potentiellement réalisable avec ajustement → **demande
  d'infos** (§2.4) plutôt que refus.

### 4.2 Erreur de prix
- **BR‑070 `[AUTO]`** : l'autorisation couvre l'estimation **+ marge**
  (`authorization_margin_pct`) + `advance_estimate` ; les petits écarts sont
  absorbés à la capture (capture ≤ autorisation).
- **BR‑071 `[OP]`** : si l'estimation est **manifestement fausse** en revue →
  **demande d'infos** ou, pour `custom`, **fixe le juste prix** à l'acceptation.
- **BR‑072 `[OP]/[ADMIN]`** : si le montant réel dépasse l'autorisation de plus de
  `price_tolerance_pct`, il faut **l'accord explicite du client** (via chat →
  réautorisation sim ou second paiement sim) **avant** capture ; sinon capture
  plafonnée à l'autorisé et le reste traité en litige `[ADMIN]`.
- **BR‑073 `[ADMIN]`** : correction d'un barème erroné dans `pricing_rules`
  (n'affecte pas rétroactivement les prix déjà **snapshotés** sur les missions).

### 4.3 Adresse incomplète
- **BR‑080 `[AUTO]`** : à la constitution, une adresse non **géocodable** bloque la
  soumission (message UX) ; les détails (étage, digicode) sont facultatifs mais
  demandés.
- **BR‑081 `[OP]`** : adresse ambiguë en revue → **demande d'infos** (BR‑031).
- **BR‑082 `[OP]`** : adresse impossible/non sécurisée → **refus** (BR‑025).

### 4.4 Client injoignable
- **BR‑090 `[OP]`** : l'intervenant tente le contact (chat, appel **simulé**).
- **BR‑091 `[AUTO]`** : après `unreachable_timeout_min` sans réponse à l'étape
  `arrived`, le système notifie le client (`operator_nearby`/relance) et l'opérateur.
- **BR‑092 `[OP]`** : si le client reste injoignable → `failed` (motif
  `client_unreachable`) ; **remboursement partiel/void** selon avancement (§5) ;
  des **frais de déplacement** peuvent s'appliquer si configuré `[ADMIN]`.

### 4.5 Intervenant indisponible
- **BR‑100 `[OP]`** : avant acceptation → ne pas accepter (ou planifier) ; peut
  **demander des infos** pour gagner du temps, ou **refuser** si aucun créneau.
- **BR‑101 `[OP]/[ADMIN]`** : après acceptation mais **avant paiement** → annuler
  (`accepted → cancelled`, acteur operator) ; aucun débit ; notif client.
- **BR‑102 `[OP]/[ADMIN]`** : après paiement (`assigned`+) et impossibilité
  d'affecter → `cancelled`/`failed` + **remboursement/void sim** intégral ; notif.
- *(Multi‑op, futur)* réaffectation `[AUTO]/[ADMIN]` à un autre intervenant.

### 4.6 Abandon de mission
- **BR‑110 `[OP]`** (intervenant) : abandon en cours → `failed` (motif
  `operator_abandon`) ; **remboursement/void sim** intégral ; incident tracé
  `[ADMIN]`.
- **BR‑111 `[OP]` (client)** : abandon/annulation par le client :
  - avant acceptation (`created/pending_review/needs_information`) : libre, sans frais ;
  - après acceptation, **dans** `cancellation_free_window_min` : **void** sim, sans frais ;
  - après ce délai et avant `in_progress` : **void/refund partiel** selon frais engagés (`advances`) — barème `[ADMIN]` ;
  - à partir de `in_progress` : annulation **non libre** ; capture éventuelle du travail réalisé + avances `[OP]/[ADMIN]`.

### 4.7 Mission impossible une fois sur place
- **BR‑120 `[OP]`** : l'intervenant déclare l'impossibilité (`* → failed`, motif) ;
  **preuve** recommandée (photo) ; notif `intervention_impossible`.
- **BR‑121 `[AUTO]/[OP]`** : remboursement sim selon avancement — void si non
  capturé, refund (total/partiel) si capturé ; **avances non récupérables**
  justifiées par ticket peuvent être retenues `[ADMIN]`.

### 4.8 Remboursements simulés
- **BR‑130 `[AUTO]`** : mapping mécanique (via `PaymentProvider`, `mock`) —
  `void` (autorisation non capturée) / `refund` (après capture) ; statuts
  `payments` : `canceled` / `refunded`. Références `sim_…`. Aucune valeur réelle.
- **BR‑131 `[OP]`** : déclenche le remboursement standard aux transitions
  d'annulation/échec.
- **BR‑132 `[ADMIN]`** : remboursement **exceptionnel** (geste commercial, litige),
  total ou partiel, avec **motif tracé** ; notif `refund_simulated`.
- **BR‑133 `[AUTO]`** : **idempotence** — un même remboursement ne peut être émis
  deux fois (clé d'événement).

### 4.9 Avances de frais
- **BR‑140** concernent les catégories dont le `category_workflow` inclut l'étape
  `shopping` (courses/pharmacie).
- **BR‑141 `[AUTO]`** : l'autorisation inclut `advance_estimate` (saisi par le
  client / défaut catégorie).
- **BR‑142 `[OP]`** : à l'achat, l'intervenant saisit `advance_actual` **avec
  ticket** (photo, bucket `mission-proofs`) — obligatoire.
- **BR‑143 `[AUTO]`** : `final_amount = prix_service + advance_actual`, capturé
  (≤ autorisation) ; `advances.reimbursed = true` (sim).
- **BR‑144 `[OP]/[ADMIN]`** : si `advance_actual` dépasse l'enveloppe autorisée +
  marge → accord client requis (BR‑072) avant capture du surplus.
- **BR‑145 `[OP]`** : un achat sans ticket ne peut pas être capturé au titre de
  l'avance (justificatif obligatoire).

### 4.10 Retards
- **BR‑150 `[AUTO]`** : si `now > ETA + delay_grace_min`, notif `mission_delayed`
  (client) ; **aucun** changement d'état.
- **BR‑151 `[OP]`** : l'intervenant informe proactivement via chat.
- **BR‑152 `[ADMIN]`** : retard grave/répété → **compensation simulée** (geste),
  et/ou incident tracé ; possible remboursement partiel.

### 4.11 Modification d'une demande en cours
- **BR‑160 `[OP]` (client)** : avant acceptation → modification **libre** (le
  client édite et re‑soumet ; `needs_information → pending_review` si en cours).
- **BR‑161 `[OP]`** : après acceptation, **modification mineure** (précision,
  détail d'accès) → acceptée par l'opérateur via chat, sans changement de prix.
- **BR‑162 `[OP]/[ADMIN]`** : **modification majeure** (change le périmètre/prix
  au‑delà de `price_tolerance_pct`) → nécessite un **nouveau prix** et une
  **réautorisation** (accord client), ou **annulation + nouvelle demande**.

### 4.12 Litiges
- **BR‑170 `[OP]/[client]`** : un litige peut être signalé pendant ou après la
  mission, dans `dispute_window_hours` suivant la clôture.
- **BR‑171 `[AUTO]`** : le système agrège les **preuves** (`mission_events`,
  photos/proofs, chat, montants) pour l'instruction.
- **BR‑172 `[ADMIN]`** : **arbitrage** — confirme/infirme, décide un
  **remboursement simulé** (total/partiel) ou le rejet, avec **motif tracé**.
- **BR‑173 `[AUTO]`** : notifications aux parties à l'ouverture et à la résolution.

### 4.13 Photos justificatives
- **BR‑180 `[AUTO]`** : stockage dans les buckets privés (`request-photos`,
  `mission-proofs`), **scoping** par propriétaire/mission (RLS), URLs signées.
- **BR‑181 `[OP]`** : l'intervenant fournit les justificatifs requis (ticket,
  état d'un lieu, pièce à identifier).
- **BR‑182 `[ADMIN]`** : une catégorie peut exiger une photo
  (`service_categories.metadata.requires_proof = true`) — **piloté par la donnée**.

### 4.14 Preuves de livraison
- **BR‑190 `[OP]`** : à la clôture (`in_progress → completed`), une **preuve de
  livraison/réalisation** est fournie (photo, ou confirmation) selon la catégorie.
- **BR‑191 `[AUTO]`** : la preuve conditionne la génération du **reçu**
  (`receipt_available`) et sert de référence en cas de litige.
- **BR‑192 `[ADMIN]`** : définit si la preuve est **obligatoire** par catégorie.

### 4.15 Force majeure
- **BR‑200 `[OP]/[ADMIN]`** : événement exceptionnel (météo grave, accident,
  sécurité) → mission `cancelled`/`failed` (motif `force_majeure`).
- **BR‑201 `[AUTO]`** : **remboursement/void sim intégral**, **aucun** frais,
  **aucune** pénalité de note pour l'intervenant ; notifs adaptées.

---

## 5. Paiement simulé — règles

- **BR‑210 `[AUTO]`** : `authorize` **refusé** si `status ≠ accepted` ou appelant
  ≠ client propriétaire (garde‑fou P1).
- **BR‑211 `[AUTO]`** : montant autorisé = `prix × (1 + margin%) + advance_estimate`.
- **BR‑212 `[AUTO]`** : `capture` à la clôture, `amount ≤ autorisé`.
- **BR‑213 `[AUTO]`** : `void` si annulation avant capture ; `refund` si après.
- **BR‑214 `[AUTO]`** : autorisation expirée (`payment_authorization_ttl_min`) →
  la mission ne peut plus démarrer sans nouvelle autorisation ; notif client.
- **BR‑215** : **pourboire** V1 **simulé** (aucun débit), tracé `tips`.
- **BR‑216** : aucune donnée de carte réelle ne transite (mock).

> Interface `PaymentProvider` (`authorize/capture/refund/void`) — cf.
> `SPEC_FONCTIONNELLE_V1.md` §5. Stripe substituable sans changer ces règles.

---

## 6. Règles temporelles (récapitulatif)

| Règle | Déclencheur | Effet | Propriété |
|---|---|---|---|
| Expiration du prix (custom) | non payé sous `quote_validity_hours` | `price_expired` ; demande refermée | `[AUTO]` |
| Retard | `now > ETA + delay_grace_min` | `mission_delayed` | `[AUTO]` |
| Client injoignable | `unreachable_timeout_min` à `arrived` | relance puis `failed` possible | `[AUTO]`+`[OP]` |
| Autorisation expirée | `payment_authorization_ttl_min` | blocage démarrage | `[AUTO]` |
| Demande d'infos sans réponse | délai (config) | auto‑annulation | `[AUTO]` |
| Fenêtre de litige | `dispute_window_hours` après clôture | ouverture possible | `[AUTO]` |

---

## 7. RGPD, rétention & modération

- **BR‑220 `[ADMIN]`** : **suppression de compte** → anonymisation des missions
  historiques nécessaires à la comptabilité, purge Storage, suppression des PII.
- **BR‑221 `[AUTO]`** : **rétention** configurable des positions et messages
  (purge `pg_cron`) — durées `[ADMIN]` (décision ouverte, à fixer).
- **BR‑222 `[AUTO]`** : **modération chat** — filtre anti‑coordonnées (téléphone,
  e‑mail) pour protéger le masque et la vie privée ; cf. `CHAT.md` (à venir).
- **BR‑223 `[AUTO]`** : **numéro masqué** prévu (Twilio, futur) ; en V1 l'appel
  est **simulé**, aucun vrai numéro échangé.
- **BR‑224 `[AUTO]`** : **journalisation** de toutes les transitions
  (`mission_events`) et des décisions de revue (acteur, horodatage, motif).

---

## 8. Matrice récapitulative des décisions

| Décision | Propriété |
|---|---|
| Vérifier zone/horaires | `[AUTO]` |
| Estimer le prix | `[AUTO]` |
| **Accepter / refuser / demander des infos** | `[OP]` |
| Fixer le prix d'une demande libre | `[OP]` |
| Affecter l'intervenant (V1) | `[AUTO]` (après paiement) |
| Déclencher chaque étape d'exécution | `[OP]` |
| Autoriser / capturer (mécanique) | `[AUTO]` (déclenché par `[OP]` à la clôture) |
| Void / refund standard | `[AUTO]` (déclenché par transition `[OP]`) |
| Remboursement exceptionnel / geste | `[ADMIN]` |
| Déclarer force majeure | `[OP]`/`[ADMIN]` |
| Arbitrer un litige | `[ADMIN]` |
| Gérer catalogue / tarifs / zones / config / rôles | `[ADMIN]` |
| Vérifier un intervenant (`is_verified`) | `[ADMIN]` |

---

## 9. Impacts modèle de données (à consolider dans `DATA_MODEL.md`)

Éléments introduits/précisés par ces règles (à intégrer sans contredire l'existant) :

- `app_config` : nouvelles clés du §0.3 (seuils). *(extension de M1.3, pas de schéma nouveau)*
- `missions.cancel_reason` : valeurs normalisées — `client_request`,
  `operator_unavailable`, `client_unreachable`, `operator_abandon`,
  `impossible_on_site`, `force_majeure`, `system_timeout`.
- **`disputes`** : **nouvelle table** (mission_id, opened_by, reason, status,
  resolution, resolved_by, amounts, timestamps) — à définir dans `DATA_MODEL.md`.
- `service_categories.metadata.requires_proof` (bool) : preuve obligatoire par
  catégorie — **piloté par la donnée** (déjà possible via `metadata`).
- `advances` : `receipt_url` obligatoire pour capturer l'avance (BR‑145).
- `mission_events.metadata` : porte le motif de décision (`review_reason`,
  `cancel_reason`), acteur et horodatage.

---

## 10. Références

`PRD.md` · `SPEC_FONCTIONNELLE_V1.md` · `UX_SPEC.md` · `Architecture_Technique.md`
· à venir : `DATA_MODEL.md`, `API_SPEC.md`, `ADMIN_PANEL.md`, `GPS_TRACKING.md`,
`NOTIFICATIONS.md`, `CHAT.md`.
