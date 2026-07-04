# Roadmap & Backlog — Barber Home

Séparation stricte des périmètres. Ce document fige la frontière entre la PR de
stabilisation (PR #1) et la couche d'expérience temps réel (PR #2).

> **Principe architectural**
> PR #1 = *core business engine* stable · PR #2 = *experience layer* temps réel.
> « Stabiliser, pas étendre. »

---

## ✅ PR #1 — Stabilisation production (scope-locked, merge-ready)

Contenu **et limite** de la PR courante :

- Auth (CLIENT / BARBER / ADMIN), sessions JWT, middleware RBAC
- Booking multi-personnes + moteur prix / durée (calcul **côté serveur**)
- Statuts de réservation (`DEMANDE_ENVOYEE → … → TERMINEE`, `ANNULEE`)
- Dashboards Client / Barber / Admin
- Prisma + PostgreSQL, seed, architecture `server/` vs `lib/`
- CI : lint · typecheck · build

**Hors périmètre PR #1 (interdit) :** GPS, carte, ETA dynamique,
websocket/realtime, refresh live, nouvelles pages, redesign UI, Stripe / SMS /
email. Les mises à jour de statut utilisent la **revalidation** (`AutoRefresh`),
pas de temps réel.

---

## 🚀 PR #2 — Couche temps réel & tracking (post-merge)

À développer dans une **branche / PR séparée**, jamais dans PR #1.

### 1. GPS Live Tracking (barber en temps réel)
- Position GPS du barber mise à jour en direct
- Affichage sur carte (Leaflet ou Google Maps)
- Suivi du trajet barber → client, mise à jour dynamique
- *Socle déjà présent* : `Barber.currentLat/Lng`, statut `EN_ROUTE`.

### 2. ETA dynamique
- Calcul basé sur la distance réelle, recalcul en déplacement
- Affichage temps réel côté client, synchronisé avec `EN_ROUTE`
- *Socle déjà présent* : `distanceKm()`, `estimateEtaMinutes()` (`src/lib/zones.ts`).

### 3. Carte interactive client
- Positions client + barber, animation du déplacement, zoom auto sur le trajet
- Interface mobile-first
- *Socle déjà présent* : `NEXT_PUBLIC_MAPS_PROVIDER` (`.env.example`).

### 4. Realtime updates (WebSocket / Supabase Realtime)
- Mise à jour live des statuts (tous les statuts du cycle)
- Notifications instantanées client & barber
- *Point d'insertion* : remplacer `AutoRefresh` + brancher `server/notifications.ts`
  sur un canal live.

### 5. Infrastructure temps réel
- Socket.io ou Supabase Realtime, updates event-driven
- Un canal par réservation, gestion déconnexion / reconnexion

---

## Politique de backlog

Toute idée de feature émergeant pendant PR #1 est **consignée ici** et **jamais
implémentée** dans la PR courante — elle est déplacée en PR séparée après merge.
