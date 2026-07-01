# GPS TRACKING — Suivi de position temps réel — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** proposition à valider
> **But :** suivre la position de l'intervenant en temps réel **de façon fluide,
> scalable, respectueuse de la vie privée**, et **pilotée par la configuration**
> (intervalles, seuils, rétention, activation) — sans code en dur, sans refonte.
>
> **Cohérence :** `Architecture_Technique.md` (§11), `DATA_MODEL.md`, `API_SPEC.md`,
> `BUSINESS_RULES.md`, `UX_SPEC.md`.

---

## 1. Principes

- **P6 — Éphémère vs persistant :** la position **haute fréquence** transite par
  **Realtime Broadcast** (aucune écriture DB par tick). La base ne reçoit que la
  **dernière position** (`operator_locations`, upsert peu fréquent) et un **tracé
  échantillonné** (`mission_tracks`).
- **Piloté par la donnée :** fréquences, seuils, précision, rétention, activation
  sont dans **`app_config`** (`gps.*`) et **`feature.*`** — modifiables sans
  redéploiement.
- **Contrôle humain & vie privée :** le suivi n'existe **que** pendant une mission
  **active** (après acceptation + affectation) ; **jamais** de suivi en dehors.
  L'intervenant **maîtrise** son partage (disponibilité/pause). Le client ne voit
  la position **que** pour sa mission en cours.
- **Simple malgré la flexibilité :** un seul canal live, deux tables persistées,
  des paramètres en base.

---

## 2. Architecture temps réel

| Canal | Type | Émis vers | Contenu |
|---|---|---|---|
| `mission:{id}:location` | **Broadcast** (éphémère) | client de la mission | position live (lat/lng/heading/speed/ts) |
| `operator:presence` | **Presence** | dispatch/opérateur | en ligne / disponibilité |
| `mission:{id}:status` | Postgres Changes | client + intervenant | transitions (déclenche l'UI carte) |

- **Broadcast** : faible latence, pas de persistance → supporte des milliers de
  flux simultanés sans charger la base.
- **Persistance échantillonnée** (voir §4) : découplée du live.

---

## 3. Cycle de vie du suivi (lié à l'état de la mission — contrôle humain)

```
created / pending_review / needs_information / accepted   → PAS de suivi
assigned                                                  → suivi ARMÉ (pré-départ)
shopping / preparing                                      → suivi optionnel (config)
en_route                                                  → suivi ACTIF (carte client ON)
arrived                                                   → suivi ACTIF (détection d'arrivée)
in_progress                                               → suivi réduit/optionnel (config)
completed / rated / cancelled / failed                    → suivi ARRÊTÉ
```

- **BR‑GPS‑01 :** le partage de position démarre **au plus tôt** à `assigned`
  (jamais avant l'acceptation humaine — P1) et s'**arrête** à la clôture/annulation.
- **BR‑GPS‑02 :** les états où la carte client est **active** sont **configurables**
  (`app_config.gps.active_states`, défaut `["en_route","arrived"]`) → adaptable
  sans code (ex. activer pendant `shopping` pour certains services).
- **BR‑GPS‑03 :** l'intervenant peut **mettre en pause** (statut `paused`) ; le
  client voit alors « position momentanément indisponible » (dernière connue).

---

## 4. Données persistées (échantillonnées)

### 4.1 `operator_locations` (dernière position)
- 1 ligne/intervenant, **upsert** peu fréquent (à intervalle `gps.upsert_sec` ou
  changement d'étape). Sert à la réouverture d'app et au **dispatch** (V2).
- `operator_id (pk)`, `location geography(point)`, `heading?`, `speed?`,
  `accuracy?`, `updated_at`. Index GIST.

### 4.2 `mission_tracks` (tracé / preuve)
- **Échantillon** (1 point / `gps.track_sample_sec`, défaut 10–20 s) — **pas**
  chaque tick. Historique + preuve de trajet.
- `id`, `mission_id`, `point geography`, `recorded_at`. Index
  `(mission_id, recorded_at)` ; **partitionnement mensuel**.

> Le flux 1 pos/1–2 s va **uniquement** sur Broadcast ; ces tables reçoivent des
> écritures **espacées**.

---

## 5. Paramètres pilotés par la donnée (`app_config.gps.*`)

| Clé | Rôle | Défaut |
|---|---|---|
| `gps.broadcast_interval_sec` | fréquence d'émission live | 1–2 |
| `gps.track_sample_sec` | échantillonnage `mission_tracks` | 15 |
| `gps.upsert_sec` | fréquence upsert `operator_locations` | 20 |
| `gps.min_distance_m` | distance mini pour émettre (anti‑bruit) | 15 |
| `gps.desired_accuracy` | précision demandée (balanced/high) | balanced |
| `gps.active_states` | états où la carte client est active | `["en_route","arrived"]` |
| `gps.background_enabled` | suivi en arrière‑plan autorisé | via `feature.gps_background` |
| `gps.nearby_radius_m` | seuil « intervenant proche » | 500 |
| `gps.arrival_radius_m` | seuil de détection d'arrivée | 80 |
| `gps.retention_days` | rétention des tracés | 30 |
| `gps.stale_after_sec` | position considérée périmée (UI repli) | 30 |

> Adapter le comportement (batterie, précision, états suivis, rétention) = éditer
> `app_config`, **sans redéploiement**, **versionné** via `CONFIG_VERSIONING.md`.

---

## 6. Côté intervenant (émission)

- **`expo-location`** : premier plan + **tâche de fond** (l'intervenant garde le
  suivi app en arrière‑plan/écran verrouillé) **si** `feature.gps_background`.
- **Fréquence adaptative** : selon vitesse/état (économie de batterie) — bornes en
  `app_config`.
- **Anti‑bruit** : n'émet que si déplacement ≥ `gps.min_distance_m`.
- **Permissions iOS** : « Lors de l'utilisation » puis « Toujours » (si background)
  — écrans de permission (UX C‑06), explication claire (App Store review).
- **Résilience** : file locale si perte réseau ; reprise à la reconnexion (seul le
  live est perdu, la dernière position est ré‑émise).

---

## 7. Côté client (réception)

- **Carte live** (`LiveMap`) : position de l'intervenant + itinéraire + ETA, mise
  à jour via Broadcast, **uniquement** dans les `gps.active_states`.
- **Repli** : si position périmée (`gps.stale_after_sec`) ou pause → afficher la
  **dernière position connue** (`operator_locations`) + mention.
- **ETA** : distance PostGIS affinée par l'API d'itinéraire (fournisseur
  configurable) ; recalcul à intervalle borné.

---

## 8. Géofencing (déclencheurs, configurables)

- **BR‑GPS‑10 « intervenant proche » :** quand distance intervenant→client ≤
  `gps.nearby_radius_m` en `en_route` → notification `operator_nearby` (une fois,
  idempotent).
- **BR‑GPS‑11 « arrivée » :** distance ≤ `gps.arrival_radius_m` → **suggère** à
  l'intervenant la transition `arrived` (proposition, l'intervenant confirme —
  contrôle humain), et/ou notifie le client.
- Calcul possible **côté serveur** (sur upsert `operator_locations`) ou **côté
  intervenant** ; seuils **en base**.
- **💡 Évolutivité :** géofences génériques futures (ex. entrée/sortie de zone,
  points d'intérêt) via une table `geofence_rules` **si** besoin — non requis en V1.

---

## 9. Sécurité & vie privée

- **RLS `operator_locations` :** l'intervenant écrit la sienne ; **seul le client
  d'une mission active** la lit ; admin. **Aucune** lecture hors mission active.
- **RLS `mission_tracks` :** participants de la mission + admin.
- **Pas de surveillance hors mission :** aucune position collectée/diffusée en
  dehors d'une mission active (P1/vie privée).
- **Rétention :** purge `pg_cron` selon `gps.retention_days` ; suppression avec le
  compte (RGPD).
- **Masquage :** l'adresse exacte du client n'est révélée que le nécessaire ;
  l'identité fine de l'intervenant reste limitée au besoin de la mission.

---

## 10. Scalabilité

- **Aucune écriture DB par tick** (Broadcast) — levier #1.
- Écritures persistées **espacées** (upsert dernière position, tracé échantillonné).
- **Partitionnement mensuel** de `mission_tracks` ; index GIST.
- Realtime ciblé (canaux par mission) ; RLS limite la diffusion aux participants.
- Charge maîtrisée par `app_config` (fréquences ajustables sous pression).

---

## 11. Évolutivité (sans refonte)

- **Multi‑intervenant (V2)** : `operator_locations` + index GIST alimentent le
  **dispatch « plus proche »** (`ORDER BY location <-> point`) sans changement de
  modèle.
- **Fournisseur d'itinéraire/ETA** configurable (Google/Mapbox) — clé `app_config`.
- **États suivis, seuils, rétention, arrière‑plan** : tous en configuration
  (versionnée) → évolution par la donnée.
- **Géofences avancées** : table dédiée additionnelle **si** un besoin réel émerge
  (registre `config_modules` prêt à l'accueillir).

---

## 12. Impacts modèle de données

- **Réutilise** `operator_locations` et `mission_tracks` (déjà au modèle).
- **Ajoute** des clés `app_config.gps.*` (§5) et `feature.gps_background` — **pas
  de nouvelle table** en V1.
- **Optionnel/futur :** `geofence_rules` (module de configuration versionné) —
  non requis en V1.

## 13. Cohérence & références

- Aligné avec l'architecture (§11) : Broadcast éphémère + persistance échantillonnée.
- Contrôle humain : suivi lié à l'état de la mission, jamais avant `assigned`,
  arrêt à la clôture ; l'arrivée est **confirmée** par l'intervenant.
- Notifications `operator_nearby` / `mission_arrived` : cf. `NOTIFICATIONS.md`
  (à venir) et `SPEC_FONCTIONNELLE_V1.md` §6.
- Références : `Architecture_Technique.md`, `DATA_MODEL.md`, `API_SPEC.md`,
  `BUSINESS_RULES.md`, `UX_SPEC.md`, `CONFIG_VERSIONING.md`.
