# Spécification fonctionnelle — V1 (démonstration)

> **Version :** 1.0 · **Statut :** validée (base pour le développement métier)
> **Documents de référence :** `docs/Architecture_Technique.md` (architecture technique, source de vérité technique).
> **Ce document** est la source de vérité **fonctionnelle** de la V1. En cas de
> divergence sur une règle métier, ce document prime ; sur un choix technique,
> l'architecture prime.

## 0. Portée & principes de la V1

- **Objectif :** démonstration complète et fonctionnelle d'un parcours de bout en bout.
- **Paiement :** **simulé** uniquement (aucun paiement réel), derrière une
  interface `PaymentProvider` permettant de brancher Stripe **sans refonte** (§5).
- **Opération :** **un seul intervenant**, **attribution automatique**,
  **acceptation immédiate** — mais l'architecture reste multi-intervenant.
- **Nom produit :** placeholder `[NOM_PRODUIT]` (inchangé pour l'instant).

### Principe directeur d'évolutivité (non négociable)

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

## 2. Machine à états de la mission

Toutes les transitions passent par **une fonction `SECURITY DEFINER`**
`transition_mission(mission_id, to_status, metadata)` qui valide
`(statut_courant, cible, rôle)` contre une **liste d'autorisations**, écrit dans
`missions`, journalise dans `mission_events`, et déclenche les effets (paiement
simulé, notifications, horodatage, temps réel). Un client ne peut **jamais**
franchir une étape réservée à l'intervenant.

### 2.1 Nouvel état `shopping`

Ajout demandé : **`accepted → shopping`** pour signaler que l'intervenant
effectue les achats. Le passage par `shopping` (et par `preparing`) est
**piloté par la donnée** (`service_categories.requires_shopping` /
`requires_preparation`), donc les services sans achat **sautent automatiquement**
cet état.

> **Impact modèle de données (à construire) :** ajouter la valeur `shopping` à
> l'enum `mission_status` (enum métier **pas encore créé** → simple ajout, aucune
> migration corrective).

### 2.2 Parcours standard (hors demande libre)

```
created → searching → assigned → accepted
        → shopping    (si requires_shopping)
        → preparing   (si requires_preparation)
        → en_route → arrived → in_progress → completed → rated (facultatif)
```

| De → Vers | Acteur | Condition / déclencheur | Effets |
|---|---|---|---|
| `created` | client | mission validée (adresse/panier OK) | snapshot prix ; **autorisation paiement simulée** |
| `created → searching` | système | autorisation sim OK → `assign-mission` | — |
| `searching → assigned` | système | attribution auto (unique intervenant dispo) | `operator_id` fixé ; notif `mission_new` |
| `assigned → accepted` | operator | acceptation immédiate (démo) | `accepted_at` ; notif `mission_accepted` |
| `accepted → shopping` | operator | **si** `requires_shopping` | notif `operator_at_store` (à l'entrée) |
| `accepted → preparing` | operator | si pas d'achat mais `requires_preparation` | notif `mission_preparing` |
| `accepted → en_route` | operator | si ni achat ni préparation | notif `mission_en_route` |
| `shopping → preparing` | operator | achats terminés + `requires_preparation` | notif `shopping_done` |
| `shopping → en_route` | operator | achats terminés, pas de préparation | notif `shopping_done` + `mission_en_route` |
| `preparing → en_route` | operator | prêt à partir | notif `mission_en_route` ; **Broadcast position ON** |
| `en_route → arrived` | operator | arrivé chez le client | notif `mission_arrived` (+ `operator_nearby` en amont via géofence) |
| `arrived → in_progress` | operator | remise / réalisation | — |
| `in_progress → completed` | operator | clôture + **montant réel** + preuve | **capture simulée** ; `completed_at` ; notif `mission_completed` + `receipt_available` ; notif différée `rating_request` |
| `completed → rated` | client | avis (**facultatif**) | recalcul `rating_avg` |

### 2.3 Annulation & échec (transverses)

| De → Vers | Acteur | Règle | Effets |
|---|---|---|---|
| `created…arrived → cancelled` | client / operator / système | avant `in_progress` | `cancel_actor` + `cancel_reason` + `cancelled_at` ; **annulation de l'autorisation sim** (remboursement sim si déjà capturé → notif `refund_simulated`) ; notif `mission_cancelled` (client) / `mission_cancelled_by_client` (operator) |
| `shopping…in_progress → failed` | operator / système | intervention impossible | preuve/raison ; remboursement sim → notif `refund_simulated` ; notif `intervention_impossible` |
| *(retard)* | système (monitor/cron) | `now > ETA + délai de grâce` (config) | notif `mission_delayed` (sans changer d'état) |

### 2.4 Branche demande libre (`custom`)

| De → Vers | Acteur | Déclencheur | Effets |
|---|---|---|---|
| `created → quote_pending` | client | demande libre soumise (pas d'estimation) | notif `quote_requested` (operator) |
| `quote_pending → quote_sent` | operator | `compose-quote` — **1 seul devis** | `operator_id` fixé ; `quotes.expires_at = +24 h` ; notif `quote_ready` |
| `quote_sent → accepted` | client | accepte le devis | **autorisation sim** → puis `preparing/en_route → … → completed` |
| `quote_sent → quote_refused` | client | refuse | terminal |
| `quote_sent → quote_refused` | système (cron) | **expiration 24 h** | `quotes.status='expired'` ; notif `quote_expired` |
| `quote_pending / quote_sent → cancelled` | client | annulation | règle d'annulation §2.3 |

### 2.5 Liste d'autorisations (allow-list de la fonction de transition)

```
created      → searching, cancelled, quote_pending
searching    → assigned, cancelled, failed
assigned     → accepted, cancelled, failed
accepted     → shopping, preparing, en_route, cancelled, failed
shopping     → preparing, en_route, cancelled, failed
preparing    → en_route, cancelled, failed
en_route     → arrived, cancelled, failed
arrived      → in_progress, cancelled, failed
in_progress  → completed, failed
completed    → rated
quote_pending→ quote_sent, cancelled
quote_sent   → accepted, quote_refused, cancelled
```

Le choix de la **prochaine étape offerte** dans l'UI (sauter `shopping`/`preparing`)
est déterminé par les flags de la catégorie — **jamais codé en dur**.

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

| Événement mission | Appel provider | `payments.status` (sim) |
|---|---|---|
| `created` (validée) | `authorize` | `requires_capture` |
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
| `mission_accepted` | → accepted | Intervenant trouvé | « {operator} prend en charge votre demande. » |
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
| `quote_ready` | → quote_sent | Devis prêt | « Votre devis : {price} € (~{eta} min). Valable 24 h. » |
| `quote_expired` | expiration 24 h | Devis expiré | « Votre devis a expiré. » |
| `rating_request` | → completed (différé) | Votre avis ? | « Comment s'est passée votre expérience avec {operator} ? » |
| `chat_message` | nouveau message | Nouveau message | « {sender} : {extrait} » |

### 6.2 Destinataire INTERVENANT

| `type` | Déclencheur | Titre | Corps |
|---|---|---|---|
| `mission_new` | → assigned | Nouvelle mission | « {category} · {distance} km · {price} €. » |
| `quote_requested` | → quote_pending | Devis à composer | « Nouvelle demande libre à chiffrer. » |
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
| enum `mission_status` | **à créer** avec la valeur supplémentaire `shopping` |
| `service_categories` | à créer avec `requires_shopping`, `requires_preparation`, `prep_buffer_min` |
| `pricing_rules` | **nouvelle table** (§3.1) |
| `pricing_modifiers` | **nouvelle table** (§3.3) |
| `app_config` | **nouvelle table** clé/valeur (§4) |
| `_shared/payments/` | interface `PaymentProvider` + `MockPaymentProvider` (§5) |
| catalogue notifications | table/paramétrage des types & textes (§6) |

## 8. Compatibilité avec le socle gelé

- Enums/tables **métier non encore créés** → ajouts sans rupture (dont `shopping`).
- `service_categories`, `coverage_zones`, `service_windows`, `payments`,
  `advances`, `tips` : déjà prévus au schéma cible de l'architecture (§6).
- RLS admin déjà en place (`current_user_role() = 'admin'`) → administrabilité
  du catalogue/tarifs directement branchable.
- Squelette Edge Functions (`_shared/`) prêt à accueillir `PaymentProvider`,
  `estimate-price`, `assign-mission`, `compose-quote`, `send-push`.
- Buckets Storage prêts ; la policy « participant de mission » sur
  `mission-proofs` sera ajoutée avec la table `missions` (M12).
