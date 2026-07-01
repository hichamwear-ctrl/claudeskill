# Spécification fonctionnelle — V1 (démonstration)

> **Version :** 1.1 · **Statut :** validée (base pour le développement métier)
>
> **Changement v1.1 — Validation opérateur obligatoire :** aucune mission n'est
> créée ni payée automatiquement. Toute demande passe par une **revue humaine**
> (opérateur) avant acceptation et avant tout paiement. Voir §0 (principe) et §2.
> **Documents de référence :** `docs/Architecture_Technique.md` (architecture technique, source de vérité technique).
> **Ce document** est la source de vérité **fonctionnelle** de la V1. En cas de
> divergence sur une règle métier, ce document prime ; sur un choix technique,
> l'architecture prime.

## 0. Portée & principes de la V1

- **Objectif :** démonstration complète et fonctionnelle d'un parcours de bout en bout.
- **Paiement :** **simulé** uniquement (aucun paiement réel), derrière une
  interface `PaymentProvider` permettant de brancher Stripe **sans refonte** (§5).
  Le paiement n'est **jamais** proposé avant l'acceptation opérateur (§2).
- **Opération :** **un seul intervenant**, **affectation automatique après
  acceptation** — mais l'architecture reste multi-intervenant.
- **Nom produit :** placeholder `[NOM_PRODUIT]` (inchangé pour l'instant).

### Principe directeur n°1 — Contrôle humain total (non négociable)

> **Aucune mission n'est créée ni payée automatiquement.** Toute demande, même
> parfaitement comprise, est soumise à une **décision humaine** d'un opérateur
> (rôle `operator`, ou `admin`) avant acceptation. Le client :
> - ne peut **jamais** forcer la création d'une mission (il ne dépasse jamais
>   l'état `pending_review` de sa propre initiative) ;
> - ne peut **jamais** payer tant que la demande n'a pas été **acceptée**.
>
> L'IA/UX peut assister la constitution de la demande, mais la décision finale
> (accepter / refuser / demander des informations) appartient toujours à
> l'opérateur. Cette règle prime sur toute automatisation.

### Principe directeur n°2 — Évolutivité (non négociable)

> **Aucune règle métier codée en dur.** Tout ce qui est susceptible de changer
> (catalogue, tarifs, délais, textes, zones, horaires, seuils, suppléments,
> validité des devis, marges) vit **en base de données ou en configuration**,
> et sera **administrable** via le futur panneau d'administration (M13).
> Le code lit ces valeurs ; il ne les contient pas.

Tables/config « pilotables » : `service_categories`, `pricing_rules`,
`pricing_modifiers`, `coverage_zones`, `service_windows`, `app_config`
(clé/valeur pour les seuils divers). Toutes en écriture **admin** (RLS).

---

## 1. Catalogue de services (100 % administrable)

Familles = enum `mission_family` (`shopping / auto / home_service / courier / custom`).
Chaque service = **une ligne** de `service_categories`. **Aucune catégorie n'est
codée en dur** : l'app récupère le catalogue depuis la base.

### 1.1 Catalogue initial (démo)

| slug | label | famille | `requires_shopping` | `base_fee` (€) | `legal_note` |
|---|---|---|---|---|---|
| `groceries` | Courses alimentaires | shopping | oui | 4,90 | — |
| `pharmacy` | Pharmacie (sans ordonnance) | shopping | oui | 5,90 | « Produits **sans ordonnance** uniquement. » |
| `parcel` | Livraison de colis | courier | non | 5,90 | — |
| `car_assist` | Dépannage auto simple | auto | non | 9,90 | « Interventions simples (batterie, pneu, carburant). Hors remorquage. » |
| `daily_help` | Services du quotidien | home_service | non | 6,90 | — |
| `custom_request` | Demande libre | custom | non | 0,00 | Tarif fixé par **devis**. |

### 1.2 Champs administrables (CRUD admin)

L'administrateur peut **créer / modifier / désactiver** une catégorie et éditer
sans redéploiement :

| Champ | Rôle | Éditable |
|---|---|---|
| `label` | libellé affiché | ✅ |
| `icon` | icône | ✅ |
| `legal_note` | mention légale affichée | ✅ |
| `is_active` | activer/désactiver (retrait du catalogue sans suppression) | ✅ |
| `base_fee` | supplément tarifaire de la catégorie | ✅ |
| `prep_buffer_min` | délai estimé additionnel (ETA) | ✅ |
| `requires_shopping` | la mission passe-t-elle par l'état `shopping` | ✅ |
| `requires_preparation` | la mission passe-t-elle par l'état `preparing` | ✅ |
| `fulfillment` | `self` / `partner` | ✅ |
| `sort_order` | ordre d'affichage | ✅ |

> **Impact modèle de données (à construire) :** ajouter à `service_categories`
> les colonnes `requires_shopping boolean`, `requires_preparation boolean`,
> `prep_buffer_min int`. Le reste existe déjà dans le schéma cible (§6.3 archi).

---

## 2. Machine à états de la mission (avec validation opérateur)

Toutes les transitions passent par **une fonction `SECURITY DEFINER`**
`transition_mission(mission_id, to_status, metadata)` qui valide
`(statut_courant, cible, rôle)` contre une **liste d'autorisations**, écrit dans
`missions`, journalise dans `mission_events`, et déclenche les effets (paiement
simulé, notifications, horodatage, temps réel). Elle applique le **contrôle
humain** (§0 principe n°1) : le client ne franchit jamais `pending_review` seul,
et les décisions de revue sont réservées à `operator`/`admin`.

### 2.1 Vue d'ensemble

```
created (brouillon)
  └─(client « Envoyer la demande »)─▶ pending_review ──▶ push OPÉRATEUR
                                          │
        ┌── operator: refuse ────────────┤
        │                                 ├── operator: demande infos ─▶ needs_information
        ▼                                 │                                   │
     rejected (terminal)                  │        (client répond) ◀──────────┘
                                          ▼                │
                             operator: ACCEPTE            └─▶ pending_review
                                          │
                                   accepted  ──▶ notif client « acceptée »
                                          │      (PAIEMENT DÉBLOQUÉ ICI SEULEMENT)
                       (client paie: autorisation sim)
                                          ▼
                                     assigned  (intervenant affecté ; démo: auto)
                                          │
              ┌── shopping (si requires_shopping) ──┐
              ▼                                       ▼
        preparing (si requires_preparation) ──▶ en_route ─▶ arrived ─▶ in_progress
                                                                            ▼
                                                                      completed ─▶ rated (facultatif)
```

> **États ajoutés à l'enum `mission_status` :** `pending_review`,
> `needs_information`, `rejected` (+ `shopping`). **États supprimés** (consolidés
> dans la revue) : `quote_pending`, `quote_sent`, `quote_refused`.

### 2.2 Constitution & soumission (client)

| De → Vers | Acteur | Déclencheur | Effets |
|---|---|---|---|
| `created` | client | brouillon ; le client répond aux questions (chat/formulaire) | rien de figé ; **aucun paiement** |
| `created → pending_review` | client | **« Envoyer la demande »** (récapitulatif complet) | `submitted_at` ; **push opérateur** `new_request_to_review` ; notif client `request_submitted` |
| `created → cancelled` | client | abandon du brouillon | — |

### 2.3 Revue humaine (décision opérateur)

> Réservé aux rôles **`operator`** et **`admin`**. Le client ne peut jamais
> déclencher ces transitions.

| De → Vers | Acteur | Déclencheur | Effets |
|---|---|---|---|
| `pending_review → accepted` | operator/admin | accepte (fixe/valide le prix ; pour `custom`, **saisit le prix** → `quotes`, validité 24 h) | `reviewed_at`, `reviewed_by` ; notif client `request_accepted` ; **paiement débloqué** |
| `pending_review → rejected` | operator/admin | refuse | `review_reason` ; notif client `request_rejected` (terminal) |
| `pending_review → needs_information` | operator/admin | demande des infos | `review_reason` ; notif client `request_needs_info` ; **rouvre la conversation** |
| `needs_information → pending_review` | client | répond aux nouvelles questions (chat) | nouvelle soumission ; push opérateur |
| `pending_review / needs_information → cancelled` | client | retire sa demande | — |

**Tableau de bord de revue (lecture seule)** présenté à l'opérateur : disponibilité
de l'équipe (`operator_profiles.status` / Presence), charge (nb de missions
actives), missions en cours, **localisation des intervenants** (`operator_locations`).

### 2.4 Paiement (gate) puis affectation

| De → Vers | Acteur | Règle | Effets |
|---|---|---|---|
| *(paiement)* | client | possible **uniquement si `status = accepted`** | `PaymentProvider.authorize` (sim) → `payments.status = requires_capture` |
| `accepted → assigned` | système | **après autorisation sim réussie** ; affecte l'intervenant (démo : auto) | `operator_id` fixé ; notif `mission_new` (intervenant) |
| `accepted → cancelled` | client/operator | renoncement avant paiement / annulation | `void` sim si autorisation existante |

> `searching` reste dans l'enum, **réservé au dispatch multi-intervenant** (phase
> de recherche asynchrone d'un intervenant après paiement). En V1 mono-intervenant,
> on passe directement `accepted → assigned`.

### 2.5 Exécution

| De → Vers | Acteur | Condition | Effets |
|---|---|---|---|
| `assigned → shopping` | operator | **si** `requires_shopping` | notif `operator_at_store` |
| `assigned → preparing` | operator | sinon, **si** `requires_preparation` | notif `mission_preparing` |
| `assigned → en_route` | operator | sinon | notif `mission_en_route` |
| `shopping → preparing` | operator | achats finis + `requires_preparation` | notif `shopping_done` |
| `shopping → en_route` | operator | achats finis, sans préparation | `shopping_done` + `mission_en_route` |
| `preparing → en_route` | operator | prêt à partir | notif `mission_en_route` ; **Broadcast position ON** |
| `en_route → arrived` | operator | arrivé chez le client | `mission_arrived` (+ `operator_nearby` via géofence) |
| `arrived → in_progress` | operator | remise / réalisation | — |
| `in_progress → completed` | operator | clôture + montant réel + preuve | **capture sim** ; `completed_at` ; `mission_completed` + `receipt_available` ; `rating_request` (différé) |
| `completed → rated` | client | avis (**facultatif**) | recalcul `rating_avg` |

### 2.6 Annulation & échec (transverses)

| De → Vers | Acteur | Règle | Effets |
|---|---|---|---|
| `accepted…arrived → cancelled` | client / operator / système | avant `in_progress` | `cancel_actor`+`cancel_reason`+`cancelled_at` ; **`void`/`refund` sim** ; `mission_cancelled` / `mission_cancelled_by_client` |
| `shopping…in_progress → failed` | operator / système | intervention impossible | preuve/raison ; **remboursement sim** → `refund_simulated` ; `intervention_impossible` |
| *(retard)* | système (cron) | `now > ETA + délai de grâce` (config) | `mission_delayed` (sans changer d'état) |
| `pending_review → cancelled` (expiration) | système (cron) | prix proposé non payé sous **24 h** (`custom`) | `rejected`/`cancelled` ; notif client |

### 2.7 Liste d'autorisations (allow-list de `transition_mission`)

```
created           → pending_review [client], cancelled [client]
pending_review    → accepted [operator/admin], rejected [operator/admin],
                    needs_information [operator/admin], cancelled [client]
needs_information → pending_review [client], cancelled [client]
accepted          → assigned [system: paiement autorisé], cancelled [client/operator]
assigned          → shopping [operator], preparing [operator], en_route [operator],
                    cancelled [client/operator], failed [operator]
shopping          → preparing, en_route, cancelled, failed [operator]
preparing         → en_route, cancelled, failed [operator]
en_route          → arrived, cancelled, failed [operator]
arrived           → in_progress, cancelled, failed [operator]
in_progress       → completed, failed [operator]
completed         → rated [client]
```

Le rôle autorisé est indiqué entre crochets. Le choix de l'étape offerte dans
l'UI (saut de `shopping`/`preparing`) dépend des flags de catégorie — jamais codé
en dur.

---

## 3. Tarification (paramètres 100 % en base, administrables)

Aucun tarif dans le code. `estimate-price` **lit** tous les paramètres en base.

### 3.1 `pricing_rules` (1 ligne par zone ; `zone_id NULL` = défaut global)

| Paramètre | Rôle | Valeur démo |
|---|---|---|
| `base_fare` | frais de base commande | 3,50 € |
| `price_per_km` | prix au km | 0,90 €/km |
| `minimum_price` | prix plancher | 5,00 € |
| `authorization_margin_pct` | marge d'autorisation (sim → Stripe) | 20 % |
| `avg_speed_kmh` | pour l'ETA | 25 km/h |
| `currency` | devise | `eur` |

`service_categories.base_fee` = supplément par catégorie ; `prep_buffer_min` =
délai additionnel ETA (§1.2).

### 3.2 Formule

```
distance_km = distance(intervenant/pickup → dropoff)         (PostGIS ; routing réel plus tard)
prix_base   = base_fare + categorie.base_fee + price_per_km × distance_km
prix        = max(prix_base, minimum_price)
prix        = APPLIQUER_MODIFICATEURS(prix, contexte)         (§3.3)
eta_min     = round(distance_km / avg_speed_kmh × 60 + prep_buffer_min)
autorisation_sim = prix × (1 + authorization_margin_pct/100) + advance_estimate
```

`advance_estimate` = avance de frais estimée (panier prévu), saisie pour
`groceries`/`pharmacy`, 0 sinon. À la clôture : `advance_actual` (ticket) →
`final_amount = prix + advance_actual`, capturé (sim), ≤ autorisation.

### 3.3 Suppléments futurs — `pricing_modifiers` (extensible **sans changer l'architecture**)

Table pensée pour accueillir **nuit / week-end / jour férié / météo / urgence**
et tout futur supplément **par simple insertion de ligne** (aucune migration de
structure, aucun code métier à modifier).

| Colonne | Rôle |
|---|---|
| `id` | PK |
| `zone_id` | portée (NULL = global) |
| `type` | `night` / `weekend` / `holiday` / `weather` / `urgency` / `custom` (extensible) |
| `effect` | `multiplier` \| `fixed` |
| `value` | ex. `1.25` (mult.) ou `2.50` (fixe €) |
| `condition` | `jsonb` : plage horaire, jours, dates fériées, code météo, flag urgence… |
| `priority` | ordre d'application |
| `is_active` | activable/désactivable |
| `valid_from` / `valid_until` | fenêtre de validité |

`APPLIQUER_MODIFICATEURS` évalue les lignes **actives** dont la `condition`
matche le contexte de la commande (heure, jour, date, météo, urgence), par
`priority` : multiplicateurs composés puis montants fixes ajoutés. **Tout est en
base et éditable par l'admin.**

> **Impact modèle de données (à construire) :** créer `pricing_rules` et
> `pricing_modifiers`. Les tables paiement (`payments`, `advances`) existent déjà
> dans le schéma cible (§6.7 archi).

---

## 4. Configuration transverse — `app_config`

Table clé/valeur (`jsonb`) pour les seuils divers, **administrable**, afin de
n'avoir **aucune constante métier dans le code** :

| clé | rôle | valeur démo |
|---|---|---|
| `quote_validity_hours` | validité d'un devis | 24 |
| `nearby_radius_m` | seuil « intervenant proche » | 500 |
| `delay_grace_min` | tolérance avant « mission en retard » | 10 |
| `night_window` | plage nuit (pour supplément) | `{"from":"22:00","to":"06:00"}` |

---

## 5. Paiement simulé & interface `PaymentProvider`

La logique métier ne connaît **que** l'interface. La V1 branche une
implémentation **mock** ; Stripe se substituera plus tard **sans toucher au
reste du système**. Sélection par configuration (`app_config`/env
`PAYMENT_PROVIDER = mock | stripe`).

### 5.1 Interface (dans `supabase/functions/_shared/payments/`)

```ts
export interface PaymentProvider {
  // Empreinte à la commande (capture manuelle) : réserve les fonds.
  authorize(input: AuthorizeInput): Promise<PaymentResult>;
  // Débit du montant réel à la clôture (≤ autorisé).
  capture(input: CaptureInput): Promise<PaymentResult>;
  // Remboursement (annulation après capture, litige).
  refund(input: RefundInput): Promise<PaymentResult>;
  // Annulation d'une autorisation non capturée (fonds libérés).
  void(input: VoidInput): Promise<PaymentResult>;
}
```

### 5.2 Implémentations

- **`MockPaymentProvider` (V1) :** ne fait aucun appel externe ; génère des
  références `sim_pi_…` / `sim_re_…`, met à jour la table `payments` et reproduit
  **fidèlement** les statuts Stripe : `requires_capture → succeeded /
  partially_captured → refunded`, et `canceled` pour un `void`. Aucune donnée de
  carte.
- **`StripePaymentProvider` (futur) :** même interface, appels Stripe réels
  (PaymentIntent capture manuelle, webhook signé). **Aucun changement** côté
  machine à états ni Edge Functions métier.

### 5.3 Correspondance états paiement ↔ mission

> **Gate d'acceptation :** `authorize` est **refusé** par l'Edge Function tant que
> `missions.status ≠ accepted` **et** que l'appelant n'est pas le client
> propriétaire. Le client ne peut donc jamais payer une demande non validée (§0).

| Événement mission | Appel provider | `payments.status` (sim) |
|---|---|---|
| `accepted` + le client paie | `authorize` | `requires_capture` |
| `completed` | `capture` | `succeeded` / `partially_captured` |
| `cancelled` avant capture | `void` | `canceled` |
| `cancelled`/`failed` après capture | `refund` | `refunded` |

Le pourboire (V1) est **simulé** (aucun débit), tracé dans `tips`.

---

## 6. Catalogue complet des notifications

1 notif = 1 ligne `notifications` (in-app) + 1 push Expo, déclenchée par
transition/événement (Database Webhook → `send-push`), avec **clé d'idempotence**
et **deep-link** vers l'écran mission. Les **textes sont éditables** (catalogue en
base, pas de copie codée en dur).

### 6.1 Destinataire CLIENT

| `type` | Déclencheur | Titre | Corps (gabarit) |
|---|---|---|---|
| `request_submitted` | → pending_review | Demande envoyée | « Votre demande a bien été envoyée. Elle est en cours de validation. » |
| `request_accepted` | → accepted | Demande acceptée | « Votre demande a été acceptée. Vous pouvez procéder au paiement. » |
| `request_rejected` | → rejected | Demande non prise en charge | « Nous ne pouvons pas prendre en charge votre demande. {reason} » |
| `request_needs_info` | → needs_information | Informations demandées | « L'opérateur a besoin de précisions. Ouvrez la conversation pour répondre. » |
| `operator_at_store` | → shopping | Arrivé au magasin | « {operator} est au magasin pour vos achats. » |
| `shopping_done` | shopping → suivant | Achats terminés | « Vos achats sont terminés. » |
| `mission_preparing` | → preparing | En préparation | « Votre demande est en préparation. » |
| `mission_en_route` | → en_route | En route | « {operator} est en route (~{eta} min). » |
| `operator_nearby` | géofence (`nearby_radius_m`) | Intervenant proche | « {operator} arrive dans quelques minutes. » |
| `mission_arrived` | → arrived | Arrivé | « {operator} est arrivé. » |
| `mission_completed` | → completed | Terminé | « C'est fait ! Montant : {final_amount} €. » |
| `receipt_available` | après capture sim | Reçu disponible | « Votre reçu est disponible. » |
| `mission_delayed` | retard (`delay_grace_min`) | Léger retard | « Votre mission a un peu de retard, merci de votre patience. » |
| `intervention_impossible` | → failed | Intervention impossible | « L'intervention n'a pas pu être réalisée. {reason} » |
| `refund_simulated` | remboursement sim | Remboursement | « Un remboursement (simulé) de {amount} € a été effectué. » |
| `mission_cancelled` | → cancelled | Demande annulée | « Votre demande a été annulée. {reason} » |
| `price_expired` | prix proposé non payé sous 24 h (`custom`) | Offre expirée | « L'offre pour votre demande a expiré. » |
| `rating_request` | → completed (différé) | Votre avis ? | « Comment s'est passée votre expérience avec {operator} ? » |
| `chat_message` | nouveau message | Nouveau message | « {sender} : {extrait} » |

### 6.2 Destinataire OPÉRATEUR / INTERVENANT

| `type` | Déclencheur | Titre | Corps |
|---|---|---|---|
| `new_request_to_review` | → pending_review | Nouvelle demande à valider | « Une demande attend votre décision. » |
| `mission_new` | → assigned | Nouvelle mission | « {category} · {distance} km · {price} €. » |
| `mission_cancelled_by_client` | client annule | Mission annulée | « Le client a annulé la mission. » |
| `chat_message` | nouveau message | Nouveau message | « {sender} : {extrait} » |

Règles d'envoi : regroupement, silence nocturne côté client sauf mission active,
respect des permissions (§13.3 archi), idempotence (§13.4 archi).

---

## 7. Récapitulatif des impacts sur le modèle de données (à construire aux étapes M1–M4)

> **Backend gelé aujourd'hui.** Cette section liste ce qui sera créé lors de
> l'implémentation ; rien n'est modifié maintenant. Les enums/tables métier
> n'existent pas encore → ces ajouts se font « à neuf », sans migration corrective.

| Élément | Action |
|---|---|
| enum `mission_status` | **à créer** avec `pending_review`, `needs_information`, `rejected`, `shopping` ; **sans** `quote_pending`/`quote_sent`/`quote_refused` (consolidés dans la revue) |
| `service_categories` | ✅ créé (M1.1) avec `requires_shopping`, `requires_preparation`, `prep_buffer_min` |
| `coverage_zones` / `service_windows` / `waitlist` | ✅ créés (M1.2) |
| `missions` | à créer avec, en plus du schéma cible : `submitted_at`, `reviewed_at`, `reviewed_by uuid`, `review_reason text` |
| `mission_events` | trace déjà l'acteur/décideur de chaque transition (`actor_id`, `actor_role`) |
| `quotes` | conservée : **enregistre le prix proposé à l'acceptation** (`custom`), validité 24 h ; plus liée à des états `quote_*` |
| `pricing_rules` / `pricing_modifiers` / `app_config` | **nouvelles tables** (§3–§4) — M1.3 |
| `transition_mission()` | fonction `SECURITY DEFINER` : allow-list `(from,to,rôle)` §2.7, gate paiement, garde-fous contrôle humain |
| `_shared/payments/` | interface `PaymentProvider` + `MockPaymentProvider` (§5) ; `authorize` **gated** sur `accepted` |
| catalogue notifications | types & textes éditables (§6), dont `new_request_to_review`, `request_*` |

## 8. Compatibilité avec le socle gelé & les étapes déjà livrées

- **M1.1 (catalogue) et M1.2 (zones)** ne sont **pas impactés** par la validation
  opérateur (données de référence) → aucun rework.
- Enums/tables **missions non encore créés** → le nouveau flux (états de revue,
  suppression des `quote_*`) se construit « à neuf », sans migration corrective.
- RLS admin déjà en place (`current_user_role()`) → décisions de revue réservées
  à `operator`/`admin` directement exprimables.
- Squelette Edge Functions (`_shared/`) prêt à accueillir `PaymentProvider`
  (gated), `estimate-price`, `assign-mission`, `send-push`, et la revue via
  `transition_mission`.
- Buckets Storage prêts ; la policy « participant de mission » sur
  `mission-proofs` sera ajoutée avec la table `missions` (M12).
