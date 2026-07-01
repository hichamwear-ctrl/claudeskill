# PRD — Product Requirements Document — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **Produit :** application mobile de services & livraisons à la demande.
> **Portée de ce document :** le *pourquoi* et le *quoi* de la V1 (démonstration).
> Le *comment* détaillé vit dans les documents liés (voir §15).
>
> **Cohérence :** ce PRD est aligné avec `Architecture_Technique.md` (technique),
> `SPEC_FONCTIONNELLE_V1.md` (règles métier) et `UX_SPEC.md` (écrans). En cas de
> divergence : le PRD fixe l'intention produit ; la spec fonctionnelle prime sur
> une règle métier précise ; l'architecture prime sur un choix technique.

---

## 1. Résumé exécutif

`[NOM_PRODUIT]` met en relation des **clients** ayant un besoin du quotidien
(courses, pharmacie sans ordonnance, petit dépannage auto, livraison de colis,
services du quotidien, ou **demande libre**) avec un **intervenant** qui réalise
la mission. Particularité fondamentale de la V1 : **un opérateur humain valide
chaque demande** avant toute acceptation et tout paiement. L'objectif de cette
première version est une **démonstration complète et fonctionnelle** du parcours
de bout en bout, avec un **paiement simulé** (aucun paiement réel), une
architecture prête à accueillir Stripe et le multi‑intervenant **sans refonte**.

## 2. Vision & mission

- **Vision :** rendre accessible, en quelques minutes, l'exécution d'un besoin
  concret du quotidien, avec la fiabilité d'une décision humaine.
- **Mission V1 :** prouver le parcours complet (demande → validation humaine →
  paiement simulé → exécution suivie en temps réel → clôture → avis) sur **une
  ville**, avec **un intervenant**, de façon **crédible et démontrable**.

## 3. Problème & opportunité

- Les besoins du quotidien sont fragmentés (plusieurs apps, plusieurs métiers).
- Les plateformes 100 % automatisées acceptent des demandes qu'elles ne peuvent
  pas toujours honorer, dégradant la confiance.
- **Opportunité :** une plateforme unique, multi‑services, où **un humain garde
  le contrôle** de ce qui est accepté — gage de qualité et de maîtrise du risque,
  tout en restant scalable techniquement.

## 4. Principes directeurs (non négociables)

| # | Principe | Implication |
|---|---|---|
| **P0** | **Moteur UNIVERSEL de traitement de demandes** | L'utilisateur **ne choisit jamais** de catégorie et **ne les voit jamais**. Il décrit librement son besoin (« De quoi avez‑vous besoin aujourd'hui ? »). Le moteur traite **n'importe quelle** demande — **même inédite, jamais vue** — via un parcours **générique** si nécessaire ; une catégorie n'est **jamais requise**. La taxonomie est **100 % interne** (classification, workflow, tarif, stats, affectation, règles). On **enrichit règles/questions/classification** pour *mieux* traiter ; on ne **modifie jamais l'architecture** ni n'« ajoute un métier » pour supporter un nouveau besoin. |
| P1 | **Contrôle humain total** | Aucune mission créée ni payée automatiquement ; l'opérateur décide (accepter / refuser / demander des infos). Le client ne dépasse jamais `pending_review` seul et ne paie jamais avant acceptation. |
| P2 | **Construire pour une flotte, opérer avec une personne** | Le modèle est multi‑intervenant dès le schéma ; l'opération V1 est mono‑intervenant. |
| P3 | **Rien codé en dur** | Catalogue, tarifs, délais, textes, zones, horaires, seuils vivent en base et sont administrables. |
| P4 | **Paiement simulé, Stripe‑ready** | V1 = simulation fidèle (autorisation/capture/remboursement) derrière une interface `PaymentProvider` remplaçable par Stripe sans refonte. |
| P5 | **La base est la source de vérité** | La machine à états de la mission vit en base ; l'UI y réagit en temps réel. |
| P6 | **Sécurité par défaut** | RLS partout, refus par défaut, secrets côté serveur uniquement. |
| **P7** | **Le moteur ne connaît jamais les métiers, seulement des CAPACITÉS** | Le moteur conversationnel raisonne en **capacités** (achat, récupération, transport, livraison, réparation, installation, assistance, déplacement, manutention, diagnostic, intervention sur site, accompagnement…). Un « métier » = une **combinaison de capacités** (« acheter du lait » = achat + livraison ; « pneu crevé » = diagnostic + intervention). La taxonomie interne (catégories) sert **stats/workflow/tarif**, mais le moteur en reste **indépendant**. |
| **P8** | **Le moteur sait dire « je ne sais pas »** | Il n'**invente jamais**. Confiance faible → il **continue en questions génériques**, construit le dossier, laisse `category_id = null` si besoin, et **transmet un dossier complet à l'opérateur**. Une demande inconnue n'est **jamais** bloquée faute de catégorie. |
| **P9** | **Deux systèmes indépendants : intake ≠ exécution** | **Conversation d'intake** (comprendre le besoin → `pending_review`) et **chat de mission** (après acceptation, exécution) sont **totalement séparés** : tables, règles métier et notifications **distinctes**. |

## 5. Personas & rôles

| Rôle (technique) | Persona | Besoins clés |
|---|---|---|
| `client` | **Léa**, particulier pressé | exprimer un besoin simplement, savoir vite si c'est accepté, suivre en direct, payer en confiance |
| `operator` | **Karim**, l'opérateur‑intervenant (vous en V1) | recevoir les demandes, **décider** (accepter/refuser/demander des infos), voir sa charge et la position de l'équipe, réaliser la mission |
| `admin` | **Support / exploitation** | gérer catalogue, tarifs, zones, litiges, remboursements simulés, configuration |

> En V1 mono‑personne, `operator` et la réalisation sont la même personne ; le
> rôle `admin` peut être la même personne via le back‑office web.

## 6. Proposition de valeur

- **Client :** un seul point d'entrée pour des besoins variés ; une réponse
  humaine rapide ; un suivi transparent ; pas de paiement avant acceptation.
- **Opérateur :** maîtrise totale de ce qu'il accepte ; vision de sa charge et de
  son équipe ; outil de réalisation guidé étape par étape.
- **Plateforme :** qualité et confiance par la validation humaine ; base
  technique scalable et évolutive (multi‑intervenant, Stripe) sans réécriture.

## 7. Périmètre V1

### 7.1 Inclus
- Authentification (OTP téléphone + Sign in with Apple).
- Catalogue de 6 services (§8) sur **une ville** (Bruxelles, configurable).
- Constitution d'une demande (questions, articles, photos, adresses, remarques).
- **Soumission → validation opérateur** (accepter / refuser / demander des infos).
- **Paiement simulé** débloqué **après acceptation** (autorisation puis capture).
- Affectation automatique de l'unique intervenant après paiement.
- Exécution suivie : états de mission, **suivi GPS temps réel**, **chat**,
  **notifications** push.
- Clôture (montant réel + preuve), reçu simulé, **avis facultatif**, **pourboire
  simulé**.
- **Back‑office admin** (catalogue, tarifs, zones, config, litiges/remboursements
  simulés).

### 7.2 Exclus (V1)
- Paiement réel / Stripe (préparé, non branché).
- Multi‑intervenant / dispatch « plus proche » (préparé, non activé).
- Appels via relais Twilio (appels **simulés** en V1).
- Médicaments sur ordonnance ; remorquage auto ; services hors catalogue.
- Mode sombre (V2) ; Android (iOS d'abord).
- Codes promo, Stripe Connect / versements intervenants (V2).

## 8. Offre de services (résumé)

Le client **décrit son besoin en langage naturel** ; le moteur le traite —
**quel qu'il soit**. La **V1 traite déjà n'importe quelle demande** (serrurier,
IKEA, déménagement, gâteau à livrer, clés perdues, plombier… ou une demande
totalement inédite) via un **parcours générique** quand aucune catégorie ne
correspond, puis **validation opérateur**.

La **taxonomie interne** (6 entrées amorcées en V1 — `SPEC_FONCTIONNELLE_V1.md`
§1) n'est **ni un catalogue à compléter, ni un menu** : c'est une **optimisation**
(meilleures questions, tarif automatique, workflow, stats, affectation). Enrichir
règles/questions/classification **améliore** le traitement d'un type de besoin ;
ce n'est **jamais requis** pour l'accepter, et **jamais** une modification
d'architecture (P0).

## 9. Parcours clés (résumé)

Détail des écrans et flux dans `UX_SPEC.md` (§4–§7).

1. **Demande standard :** le client compose sa demande → **« Envoyer la
   demande »** (`pending_review`) → décision opérateur → **si acceptée**, paiement
   simulé → affectation → exécution suivie → clôture → avis.
2. **Demande libre :** idem, mais l'opérateur **fixe le prix** à l'acceptation
   (devis valable 24 h) avant paiement.
3. **Demande d'informations :** l'opérateur demande des précisions
   (`needs_information`) → le client répond dans la conversation → re‑soumission.
4. **Refus :** l'opérateur refuse (`rejected`) → le client est notifié.

## 10. Exigences fonctionnelles

> IDs traçables (`PRD-Fxx`). Détails/valeurs dans les specs liées.

| ID | Exigence |
|---|---|
| PRD-F01 | Le client s'authentifie par OTP téléphone ou Sign in with Apple. |
| PRD-F02 | Le client **décrit librement** son besoin ; le système le **classe** (IA + règles, pilotées par la base) vers un service et déclenche les **questions dynamiques** adaptées. Aucune sélection de catégorie imposée. |
| PRD-F03 | Avant toute demande, le système vérifie la **zone** et les **horaires** ; hors zone → liste d'attente. |
| PRD-F04 | Le client constitue sa demande (questions, articles, photos, adresses, remarques) et voit un **récapitulatif** avec **prix estimatif** (si applicable) et **délai**. |
| PRD-F05 | Le client **soumet** la demande (« Envoyer la demande ») ; elle passe en `pending_review`. Le client **ne peut pas** forcer sa création ni la payer à ce stade. |
| PRD-F06 | À la soumission, l'**opérateur** reçoit une **notification** et **toutes** les informations de la demande. |
| PRD-F07 | L'opérateur dispose d'un **tableau de bord** : disponibilité de l'équipe, charge, missions en cours, **localisation des intervenants**. |
| PRD-F08 | L'opérateur **décide** : **accepter** (pour une demande libre, en **fixant le prix**), **refuser**, ou **demander des informations**. |
| PRD-F09 | Sur `needs_information`, le client répond dans la **conversation** puis re‑soumet. |
| PRD-F10 | Sur acceptation, le client est notifié et le **paiement simulé est débloqué** (jamais avant). |
| PRD-F11 | Le paiement simulé reproduit **autorisation → capture → remboursement/annulation** (aucun paiement réel). |
| PRD-F12 | Après autorisation, l'**intervenant est affecté automatiquement** (V1) et la mission démarre. |
| PRD-F13 | L'exécution suit une **machine à états** (achats, préparation, en route, arrivé, en cours, terminé), avec sauts d'étapes **pilotés par la catégorie**. |
| PRD-F14 | Le client suit la mission en **temps réel** (statuts + position de l'intervenant). |
| PRD-F15 | Un **chat** relie client et intervenant ; il porte aussi les demandes d'informations. |
| PRD-F16 | Des **notifications** informent des changements d'état clés (voir `NOTIFICATIONS.md`). |
| PRD-F17 | À la clôture, l'intervenant saisit le **montant réel** + une **preuve** ; la **capture simulée** s'applique (≤ autorisation) et un **reçu** est disponible. |
| PRD-F18 | Le client peut **noter** (facultatif) et laisser un **pourboire simulé**. |
| PRD-F19 | Le client et l'opérateur peuvent **annuler** selon des règles définies ; les remboursements simulés s'appliquent. |
| PRD-F20 | L'**admin** gère catalogue, tarifs, zones/horaires, configuration, litiges et remboursements simulés **sans redéploiement**. |

## 11. Exigences non‑fonctionnelles

| ID | Exigence |
|---|---|
| PRD-NF01 | **Sécurité :** RLS sur toutes les tables, refus par défaut ; `service_role` cantonné au serveur ; secrets hors app. |
| PRD-NF02 | **Contrôle d'accès :** décisions de revue réservées à `operator`/`admin` ; paiement gaté sur `accepted`. |
| PRD-NF03 | **Scalabilité :** positions GPS haute fréquence via Realtime Broadcast (pas d'écriture DB par tick). |
| PRD-NF04 | **Performance perçue :** skeletons, référentiel mis en cache, images compressées. |
| PRD-NF05 | **RGPD :** minimisation des PII, suppression de compte, rétention configurable ; numéro masqué prévu (Twilio, futur). |
| PRD-NF06 | **Évolutivité :** paramètres métier en base ; Stripe et multi‑intervenant activables sans refonte. |
| PRD-NF07 | **i18n / A11y :** textes externalisés (locale du profil, défaut `fr`) ; contraste AA, tailles dynamiques. |
| PRD-NF08 | **Observabilité :** journal des transitions (`mission_events`), logs Edge Functions. |
| PRD-NF09 | **Plateforme :** iOS d'abord (Expo/EAS), OTA pour correctifs. |

## 12. Objectifs & métriques

**Objectif de la V1 (démo) :** dérouler **sans accroc** le parcours complet des
§9 sur la ville de démonstration, avec paiement simulé et validation humaine.

**Métriques produit cibles (post‑démo, pour information) :**
- Taux d'acceptation des demandes (décision opérateur).
- Délai médian de décision (`pending_review → accepted/rejected`).
- Taux de complétion des missions acceptées.
- Écart prix estimé / prix réel.
- Satisfaction client (note moyenne), taux d'avis.
- Taux d'annulation par acteur.

## 13. Contraintes, hypothèses & décisions ouvertes

- **Contraintes :** stack imposée (React Native/Expo, Supabase, PostgreSQL,
  Realtime, Storage) ; iOS d'abord ; démonstration mono‑ville / mono‑intervenant.
- **Hypothèses :** un seul opérateur disponible pendant la démo ; données de
  démonstration en `seed.sql`.
- **Décisions ouvertes** (à trancher avant les étapes concernées) :
  fournisseur cartes (Google/Mapbox), fournisseur OTP (Twilio ?), marge
  d'autorisation, tracking en arrière‑plan, **durées de rétention** (positions,
  messages), **nom du produit** (placeholder pour l'instant).

## 14. Phasage

| Phase | Contenu |
|---|---|
| **V1 (démo)** | Ce PRD : mono‑ville, mono‑intervenant, validation humaine, paiement **simulé**. |
| **V1.1+** | Ajustements produit issus de la démo. |
| **V2** | **Stripe réel** (via `PaymentProvider`), **multi‑intervenant** (dispatch, `payouts`), appels via **Twilio**, mode sombre, Android. |

## 15. Documents liés

- `Architecture_Technique.md` — architecture technique (source de vérité technique).
- `SPEC_FONCTIONNELLE_V1.md` — catalogue, machine à états, tarification, paiement, notifications.
- `UX_SPEC.md` — écrans, parcours, composants, erreurs, états vides, règles UX.
- À venir : `BUSINESS_RULES.md`, `DATA_MODEL.md`, `API_SPEC.md`, `ADMIN_PANEL.md`,
  `GPS_TRACKING.md`, `NOTIFICATIONS.md`, `CHAT.md`.

## 16. Glossaire

- **Demande / mission :** besoin exprimé par un client, matérialisé par une ligne
  `missions` évoluant via une machine à états.
- **Opérateur :** décideur humain (rôle `operator`, ou `admin`) qui valide les
  demandes ; en V1, aussi l'intervenant.
- **Intervenant :** celui qui réalise la mission (V1 : l'opérateur lui‑même).
- **Paiement simulé :** simulation fidèle du cycle Stripe sans transaction réelle.
- **`pending_review` :** état d'attente de décision humaine.
- **Demande libre (`custom`) :** besoin sans tarif catalogue, chiffré par
  l'opérateur à l'acceptation (devis 24 h).
