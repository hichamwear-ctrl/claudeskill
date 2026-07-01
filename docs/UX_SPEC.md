# Spécification UX / Écrans — V1 (démonstration)

> **Version :** 1.0 · **Statut :** proposition à valider
> **Sources de vérité amont :** `Architecture_Technique.md` (technique),
> `SPEC_FONCTIONNELLE_V1.md` (règles métier). En cas de divergence UX vs règle
> métier, la spec fonctionnelle prime.
>
> Ce document décrit **tous les écrans, parcours, composants, cas d'erreur, états
> vides et règles UX** de la V1. Les points notés **🔹 À valider** sont des
> décisions de conception que je propose et sur lesquelles j'attends votre accord.

---

## 0. Portée & décisions de conception

- **Deux apps mobiles** (React Native/Expo, iOS d'abord) : **Client** et
  **Intervenant (cockpit)** — une base de code, deux expériences (sélection par
  rôle après connexion).
- **Panneau d'administration = application web** séparée (back-office). ✅ validé
- **Navigation client :** barre d'onglets (Accueil, Missions, Notifications,
  Profil) + piles modales pour la création de demande et le suivi. ✅ validé
- **Navigation intervenant :** cockpit à écran unique piloté par l'état de la
  mission + pile (mission en cours, chat, gains, profil). ✅ validé
- **Langue :** français (locale du profil, i18n prête). **Thème : clair pour la
  V1** ; mode sombre ajouté ultérieurement. ✅ validé
- **Onboarding :** très court, **2 à 3 écrans maximum**, skippable — l'utilisateur
  doit pouvoir démarrer vite. ✅ validé
- **Paiement :** écrans de paiement **simulé** (cartes fictives) — aucun SDK réel.
- **Appels :** **simulés** en V1 (aucune intégration Twilio) ; l'architecture
  réserve la place d'un relais (numéro masqué) pour un ajout ultérieur. ✅ validé

### Conventions d'identifiants d'écran

`C-xx` = Client · `OP-xx` = Intervenant · `AD-xx` = Admin. (Compatibles avec les
références de l'architecture : C-16 validation, C-19 suivi carte, C-23 appel
masqué, C-25 pourboire, OP-06 saisie montant, OP-07 clôture.)

---

## 1. Règles UX transverses

1. **Une action primaire par écran** (un seul CTA proéminent, bas de page/collant).
2. **La base est la source de vérité** : l'UI **réagit en temps réel** aux
   transitions (Realtime) — pas d'état local qui diverge du serveur.
3. **UI optimiste** seulement pour les actions réversibles et sûres ; jamais pour
   les transitions de mission ou le paiement (on attend la confirmation serveur).
4. **Toujours 4 états par écran de données** : *chargement* (skeleton), *vide*,
   *erreur* (avec réessayer), *contenu*.
5. **Feedback systématique** : toast/snackbar sur succès, bannière sur erreur,
   retour haptique sur les transitions clés (acceptée, arrivé, terminé).
6. **Zéro règle métier figée dans l'app** : catalogue, prix, délais, textes,
   zones, seuils sont **chargés depuis la base** (mise en cache du référentiel).
7. **Sécurité/vie privée** : numéro masqué (appel via relais), pas d'affichage de
   PII inutile ; l'intervenant ne voit du client que le nécessaire à la mission.
8. **Accessibilité** : cibles tactiles ≥ 44 px, contraste AA, taille de texte
   dynamique, libellés d'accessibilité sur icônes/boutons.
9. **Résilience** : hors-ligne géré (bannière + file d'attente lecture seule),
   reprise d'app sur mission active (deep-link).
10. **Cohérence** : mêmes composants (statuts, prix, cartes mission) partout.

---

## 2. États globaux (systématiques)

| État | Déclencheur | UX |
|---|---|---|
| **Chargement** | fetch en cours | skeletons (jamais de spinner plein écran hors splash) |
| **Vide** | aucune donnée | illustration + message + CTA (cf. §9) |
| **Erreur** | échec réseau/serveur | bannière/carte + bouton **Réessayer** ; message clair, pas de code brut |
| **Hors-ligne** | perte réseau | bannière persistante « Hors connexion » ; actions d'écriture désactivées |
| **Permission refusée** | localisation/notifications | écran explicatif + bouton vers réglages système |
| **Session expirée** | JWT invalide | redirection douce vers l'auth, message non alarmant |
| **Zone non couverte** | `zone-check` négatif | écran dédié + inscription liste d'attente (C-09) |
| **Hors horaires** | `service_windows` fermé | message + prochain créneau d'ouverture |
| **Limite atteinte** | rate-limit OTP | message + minuterie avant nouvel envoi |

---

## 3. Composants communs

| Composant | Usage |
|---|---|
| `Button` (primary / secondary / ghost / destructive) | actions |
| `OtpInput` | saisie code à 6 chiffres |
| `PhoneInput` | numéro + indicatif |
| `CategoryCard` | tuile de catégorie (icône, label, à partir de X €) |
| `MissionCard` | résumé mission (statut, catégorie, prix, heure) |
| `StatusBadge` | pastille d'état mission (couleur + libellé, mappe `mission_status`) |
| `MissionTimeline` / `Stepper` | progression des étapes (créée→…→terminée) |
| `LiveMap` | carte + position intervenant temps réel + itinéraire |
| `PriceBreakdown` | détail prix (base, catégorie, km, avance, marge, total) |
| `AddressPicker` | recherche/autocomplétion + carte + carnet |
| `PhotoPicker` | prise/sélection + compression (upload Storage) |
| `ChatBubble` / `ChatComposer` | messagerie + indicateur de frappe |
| `RatingStars` | notation 1–5 + tags |
| `BottomSheet` | actions contextuelles, sélection |
| `ConfirmDialog` | confirmation d'action sensible (annulation, clôture) |
| `Toast` / `Banner` | feedback succès/erreur/info |
| `Skeleton` | placeholders de chargement |
| `EmptyState` | illustration + message + CTA |
| `Avatar` | photo profil (bucket `avatars`) |
| `AvailabilityToggle` | dispo intervenant (online/offline → Presence) |

---

## 4. Écrans CLIENT

### 4.1 Inventaire

| ID | Écran | But |
|---|---|---|
| C-01 | Splash / bootstrap | init, session, config/référentiel |
| C-02 | Onboarding | 2–3 slides de présentation (skippable) |
| C-03 | Connexion — téléphone | saisie n° → OTP ; bouton **Apple** |
| C-04 | Connexion — code OTP | saisie code 6 chiffres |
| C-05 | Profil — complétion | prénom (+ avatar optionnel) |
| C-06 | Permissions | localisation & notifications |
| C-07 | Accueil / catalogue | familles + catégories (depuis la base) |
| C-08 | Zone non couverte | message + liste d'attente |
| C-09 | Création de demande | articles/instructions (catégories `self`) |
| C-10 | Demande libre | texte libre + photos (custom) |
| C-11 | Adresse de livraison | sélection/ajout, carte, détails (étage, digicode) |
| C-12 | Carnet d'adresses | gérer ses adresses |
| C-13 | Récapitulatif & estimation | prix + ETA (`estimate-price`) + avance estimée |
| C-14 | Moyen de paiement (simulé) | carte fictive par défaut |
| C-15 | Validation commande | confirme → **autorisation sim** (C-16 archi) |
| C-16 | Recherche d'intervenant | état `searching` (animation) |
| C-17 | Suivi mission | timeline + statut + actions (chat, appel, annuler) |
| C-18 | Suivi carte temps réel | position live (C-19 archi) |
| C-19 | Détail devis | accepter/refuser (custom, `quote_sent`) |
| C-20 | Chat mission | messagerie |
| C-21 | Appel (simulé) | appel simulé en V1 ; relais/numéro masqué prêt pour ajout futur (C-23 archi) |
| C-22 | Clôture & reçu | montant final + reçu sim (`completed`) |
| C-23 | Notation | avis facultatif (étoiles + tags + commentaire) |
| C-24 | Pourboire (simulé) | montants prédéfinis (C-25 archi) |
| C-25 | Annulation | choix du motif |
| C-26 | Mes missions | historique + mission active |
| C-27 | Détail mission passée | récapitulatif + reçu |
| C-28 | Notifications | liste in-app |
| C-29 | Profil & paramètres | profil, adresses, langue, déconnexion, RGPD |

### 4.2 Détail des écrans clés (format compact : contenu · actions · états)

- **C-03 Connexion téléphone** — champ n° + CTA « Recevoir le code » · bouton
  Apple · *erreurs* : n° invalide, rate-limit (minuterie) · *vide* n/a.
- **C-04 Code OTP** — 6 cases + renvoi (minuterie) · *erreurs* : code faux
  (compteur d'essais), expiré · auto-submit à la 6ᵉ.
- **C-07 Accueil/catalogue** — familles en sections, `CategoryCard` « à partir de
  X € » · barre d'adresse en tête (zone active) · *chargement* skeletons ·
  *vide* : « Aucun service disponible ici » + liste d'attente · *erreur* réessayer.
- **C-09 Création de demande** — liste d'articles (ajout/quantité/notes) ou champ
  simple selon catégorie · avance estimée (panier prévu) pour `groceries`/`pharmacy`
  · mention légale affichée (`legal_note`) · CTA « Continuer ».
- **C-13 Récapitulatif** — `PriceBreakdown` (base + catégorie + km + avance +
  marge), ETA · adresse · CTA « Valider et payer » · *erreur estimation* :
  réessayer/modifier · **hors zone/horaires** → écran dédié.
- **C-15 Validation** — récap + moyen de paiement (sim) · CTA « Confirmer » →
  autorisation sim → `searching` · *erreur paiement sim* (si configuré) : message
  + réessayer.
- **C-17 Suivi mission** — `MissionTimeline` (créée→…→terminée, saut auto de
  `shopping`/`preparing` selon catégorie) · `StatusBadge` · encart intervenant
  (avatar, prénom, note) · boutons **Chat**, **Appeler**, **Annuler** (selon état)
  · notifications d'étape reflétées en direct.
- **C-18 Carte temps réel** — position live (Broadcast), itinéraire, ETA · repli
  si position indisponible (dernière connue).
- **C-19 Détail devis** — prix, ETA, note intervenant, **validité 24 h (minuterie)**
  · CTA **Accepter** (→ autorisation sim) / **Refuser** · *expiré* : état verrouillé.
- **C-22 Clôture & reçu** — montant final, détail (service + avance réelle), reçu
  sim téléchargeable · CTA « Noter » (facultatif) / « Laisser un pourboire ».
- **C-25 Annulation** — liste de motifs (config) · avertissement conséquences
  (remboursement sim) · confirmation.

---

## 5. Écrans INTERVENANT (cockpit)

### 5.1 Inventaire

| ID | Écran | But |
|---|---|---|
| OP-01 | Connexion | identique client (rôle operator) |
| OP-02 | Profil intervenant / vérification | véhicule, documents (`is_verified`) |
| OP-03 | Cockpit / disponibilité | toggle online/offline (Presence), mission active |
| OP-04 | Mission entrante | notification `assigned` → **Accepter** (immédiat) |
| OP-05 | Mission en cours | étapes : `shopping`/`preparing`/`en_route`/`arrived`/`in_progress` |
| OP-06 | Saisie montant réel + ticket | montant + photo ticket (proof) |
| OP-07 | Clôture | confirme → **capture sim** → `completed` |
| OP-08 | Navigation carte | itinéraire pickup/dropoff |
| OP-09 | Chat mission | messagerie |
| OP-10 | Composer un devis | demande libre → prix + ETA + note |
| OP-11 | Gains & avances | récap (simulé), avances de frais |
| OP-12 | Historique missions | passées |
| OP-13 | Intervention impossible | → `failed` (motif + preuve) |
| OP-14 | Profil & paramètres | profil, langue, déconnexion, RGPD |

### 5.2 Détail des écrans clés

- **OP-03 Cockpit** — `AvailabilityToggle` (alimente Presence/dispo) · carte de
  mission active si présente · *vide* (disponible, aucune mission) : « En attente
  de missions » · *offline* : missions en pause.
- **OP-04 Mission entrante** — résumé (catégorie, distance, prix, adresse) · CTA
  **Accepter** (démo : immédiat) · minuterie/déclin possible (archi multi-op).
- **OP-05 Mission en cours** — **bouton d'étape unique contextuel** qui avance
  l'état selon la catégorie (saut auto `shopping`/`preparing` via
  `requires_shopping`/`requires_preparation`) · accès Chat, Navigation, Appel ·
  chaque appui = `transition_mission` (confirmation serveur avant maj UI).
- **OP-06 Saisie montant réel** — montant réel + `PhotoPicker` ticket (upload
  `mission-proofs`) · validation (montant ≤ autorisation, sinon avertissement
  accord client) · *erreur upload* : réessayer.
- **OP-07 Clôture** — récap + CTA « Clôturer » → capture sim → `completed`.
- **OP-10 Composer un devis** — prix + ETA + note · rappel **1 devis / 24 h** ·
  CTA « Envoyer le devis » → `quote_sent`.
- **OP-13 Intervention impossible** — motif (config) + preuve → `failed` →
  remboursement sim.

---

## 6. Écrans ADMIN (back-office web)

| ID | Écran | But |
|---|---|---|
| AD-01 | Connexion admin | accès sécurisé (rôle `admin`) |
| AD-02 | Tableau de bord | KPIs (missions par statut, du jour, en cours) |
| AD-03 | Missions — liste | recherche/filtre par statut, date, catégorie |
| AD-04 | Mission — détail | timeline (`mission_events`), paiement sim, chat, preuves |
| AD-05 | Catalogue — CRUD | créer/modifier/désactiver catégories, tarifs, délais, textes |
| AD-06 | Tarification | `pricing_rules` + `pricing_modifiers` (nuit/week-end/férié/météo/urgence) |
| AD-07 | Zones & horaires | `coverage_zones` (carte/polygone) + `service_windows` |
| AD-08 | Utilisateurs | clients/intervenants, rôles, vérification intervenant |
| AD-09 | Litiges & remboursements | déclencher un remboursement **simulé** |
| AD-10 | Notifications | catalogue des types + édition des textes |
| AD-11 | Configuration | `app_config` (seuils : validité devis, rayon « proche », retard…) |
| AD-12 | Liste d'attente | demandes hors zone (`waitlist`) |

Règles admin : **tout est éditable sans redéploiement** ; chaque écriture est
tracée ; actions sensibles (remboursement, changement de rôle) confirmées.

---

## 7. Parcours utilisateurs (flows)

### 7.1 Client — commande standard (avec achats)
```
C-03/04 Auth → C-05 profil → C-06 permissions → C-07 catalogue
→ C-09 demande (articles + avance estimée) → C-11 adresse
→ C-13 estimation (zone-check + estimate-price) → C-15 validation (autorisation sim)
→ C-16 recherche → [assigned/accepted] → C-17 suivi (shopping→…→arrived)
→ C-18 carte live → in_progress → C-22 reçu → C-23 note (facultatif) → C-24 pourboire (sim)
```

### 7.2 Client — demande libre (devis)
```
C-07 → C-10 demande libre (texte + photos) → soumission (quote_pending)
→ notif quote_ready → C-19 devis (accepter avant 24 h)
→ autorisation sim → suivi standard → reçu
```

### 7.3 Intervenant — réalisation
```
OP-03 dispo (Presence) → notif mission_new → OP-04 accepter
→ OP-05 étapes (shopping → achats → OP-06 montant+ticket) → preparing/en_route
→ OP-08 navigation → arrived → in_progress → OP-07 clôture (capture sim) → completed
```

### 7.4 Intervenant — devis
```
notif quote_requested → OP-10 composer devis → quote_sent
→ (client accepte) → OP-05 réalisation
```

### 7.5 Admin — exploitation
```
AD-02 dashboard → AD-03/04 suivi & détail mission
→ AD-05/06/07 gérer catalogue/tarifs/zones → AD-09 remboursement sim → AD-11 config
```

### 7.6 Annulation / échec
```
Client C-25 (motif) OU Intervenant OP-13 (impossible)
→ cancelled/failed → remboursement/void sim → notifs (mission_cancelled / refund_simulated)
```

---

## 8. Catalogue des cas d'erreur

| Code UX | Contexte | Message (ton rassurant) | Action |
|---|---|---|---|
| `ERR_NETWORK` | réseau indisponible | « Connexion perdue. » | Réessayer / mode hors-ligne |
| `ERR_OTP_INVALID` | code faux | « Code incorrect. » | Ressaisir (compteur) |
| `ERR_OTP_EXPIRED` | code expiré | « Ce code a expiré. » | Renvoyer |
| `ERR_RATE_LIMIT` | trop de tentatives | « Trop d'essais, réessayez dans {t}. » | Minuterie |
| `ERR_ZONE_UNCOVERED` | hors zone | « Pas encore disponible chez vous. » | Liste d'attente |
| `ERR_OUT_OF_HOURS` | hors horaires | « Service fermé. Ouverture {créneau}. » | Planifier plus tard |
| `ERR_LOCATION_OFF` | géoloc désactivée | « Activez la localisation. » | Réglages |
| `ERR_ESTIMATE` | échec estimation | « Impossible d'estimer le prix. » | Réessayer/Modifier |
| `ERR_PAYMENT_SIM` | paiement sim refusé (config) | « Paiement refusé (simulation). » | Changer de carte fictive |
| `ERR_UPLOAD` | upload photo/ticket | « Envoi de l'image échoué. » | Réessayer |
| `ERR_QUOTE_EXPIRED` | devis expiré | « Ce devis a expiré. » | Nouvelle demande |
| `ERR_MISSION_GONE` | mission annulée par l'autre partie | « La mission n'est plus disponible. » | Retour accueil |
| `ERR_NO_OPERATOR` | aucun intervenant (multi-op futur) | « Aucun intervenant disponible. » | Réessayer plus tard |
| `ERR_PERMISSION_NOTIF` | notifs refusées | « Notifications désactivées. » | Réglages |
| `ERR_SESSION` | session expirée | « Reconnectez-vous. » | Auth |

> Chaque code UX se mappe sur les erreurs `HttpError` des Edge Functions
> (statut + code) — cohérence front/back garantie.

---

## 9. Catalogue des états vides

| Écran | État vide | Message + CTA |
|---|---|---|
| C-07 catalogue | aucune catégorie en zone | « Rien ici pour l'instant » → liste d'attente |
| C-12 carnet d'adresses | aucune adresse | « Ajoutez votre première adresse » → ajouter |
| C-26 mes missions | aucune mission | « Vous n'avez pas encore de mission » → catalogue |
| C-28 notifications | vide | « Aucune notification » |
| C-20 chat | aucun message | « Démarrez la conversation » |
| OP-03 cockpit | disponible, sans mission | « En attente de missions » |
| OP-11 gains | aucun gain | « Vos gains apparaîtront ici » |
| OP-12 historique | vide | « Aucune mission réalisée » |
| AD-03 missions | filtre sans résultat | « Aucune mission pour ces critères » → réinitialiser |
| AD-12 liste d'attente | vide | « Aucune demande hors zone » |

---

## 10. Accessibilité & internationalisation

- **i18n :** tous les textes externalisés (clés), locale depuis `profiles.locale`
  (défaut `fr`) ; textes de notifications/catalogue **éditables en base**.
- **A11y :** contraste AA, taille dynamique, libellés d'accessibilité, focus
  visibles, retours haptiques, pas d'information portée par la seule couleur
  (statuts = couleur **+** libellé).
- **Performance perçue :** skeletons, préchargement du référentiel, cartes
  optimisées, images compressées à l'upload.

---

## 11. Traçabilité écrans ↔ fonctionnalités (extrait)

| Écran | Fonction / API | Table(s) |
|---|---|---|
| C-07 | lecture catalogue | `service_categories` |
| C-13 | `zone-check`, `estimate-price` | `coverage_zones`, `service_windows`, `pricing_rules`, `pricing_modifiers` |
| C-15 | `PaymentProvider.authorize` (sim) | `payments` |
| C-16→ | `assign-mission` | `missions`, `mission_events` |
| C-17/18 | Realtime status + Broadcast position | `missions`, `operator_locations`, `mission_tracks` |
| C-19 | `compose-quote` / acceptation | `quotes` |
| C-20 | chat Realtime | `messages` |
| C-22 | `PaymentProvider.capture` (sim) | `payments`, `advances` |
| C-23/24 | notation / pourboire sim | `ratings`, `tips` |
| OP-05 | `transition_mission` | `missions`, `mission_events` |
| OP-06 | upload preuve | Storage `mission-proofs`, `advances` |
| AD-05/06/07 | CRUD admin | `service_categories`, `pricing_*`, `coverage_zones`, `service_windows`, `app_config` |
| toutes | `send-push` | `notifications`, `device_tokens` |

---

## 12. Décisions de conception — validées

1. **Admin = application web** séparée. ✅
2. **Navigation client** = barre d'onglets (Accueil / Missions / Notifications / Profil). ✅
3. **Navigation intervenant** = cockpit piloté par l'état de la mission. ✅
4. **Thème** = clair pour la V1 ; mode sombre ultérieur. ✅
5. **Onboarding** = très court, 2–3 écrans max, skippable. ✅
6. **Appels** = simulés en V1, aucune intégration Twilio ; architecture prête pour ajout ultérieur. ✅
7. **Numérotation des écrans** (C- / OP- / AD-). ✅

Documentation produit **complète et validée** : source de vérité du projet.
