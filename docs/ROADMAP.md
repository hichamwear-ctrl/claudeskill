# Roadmap — Barber Home

## Convention de numérotation (source de vérité)

Le projet est organisé en **4 grandes phases produit**. C'est la seule
numérotation utilisée dans les échanges. Les découpages techniques (transport
temps réel, hooks, providers, migrations, etc.) sont des **sous-tâches
internes** — ils n'apparaissent jamais comme des « phases » côté produit.

Règle de livraison : **un prompt = une phase produit complète**, menée jusqu'à
son terme (fonctionnalités, composants, services, intégrations, tests, docs,
gates verts, zéro régression) avant tout arrêt. Aucune phase suivante n'est
entamée sans feu vert explicite.

| Phase produit | État |
|---|---|
| **Phase 1 — Core Platform** | ✅ Terminée (figée) |
| **Phase 2 — Expérience Premium** | ⏳ À développer |
| **Phase 3 — Fonctionnalités Premium** | ⏳ À développer |
| **Phase 4 — Production & Scalabilité** | ⏳ À développer |

---

## ✅ Phase 1 — Core Platform (terminée, figée)

Socle stable. Aucune modification hormis bug critique.

- Auth (CLIENT / BARBER / ADMIN), sessions JWT, middleware RBAC
- Booking multi-personnes + moteur prix / durée (calcul **côté serveur**)
- Statuts de réservation (`DEMANDE_ENVOYEE → … → TERMINEE`, `ANNULEE`)
- Dashboards Client / Barber / Admin
- Prisma + PostgreSQL, seed, architecture `server/` vs `lib/`
- CI (lint · typecheck · test · build), stabilisation

Livrée par la branche `claude/barber-home-saas-g2588t`.

---

## 🚀 Phase 2 — Expérience Premium

Tout ce qui améliore l'**expérience utilisateur** (aucune logique métier
nouvelle). Sous-tâches internes indicatives :

- Refonte visuelle premium & cohérence design system
- Landing page complète, animations (Framer Motion), micro-interactions
- Responsive mobile-first affiné sur tous les breakpoints
- UX du flow de réservation (fluidité, états, feedback)
- Dashboards améliorés (hiérarchie visuelle, états vides, skeletons)
- Imagerie professionnelle (barbershop), optimisation `next/image`
- SEO (metadata, OG, sitemap, JSON-LD) approfondi
- Performances front (code-splitting, lazy, LCP/CLS)
- Accessibilité (WCAG : contraste, clavier, ARIA, focus)

---

## 📍 Phase 3 — Fonctionnalités Premium

Ensemble des **fonctionnalités avancées**. Sous-tâches internes indicatives :

- Temps réel (Supabase Realtime — **infra transport déjà amorcée en interne** :
  `src/lib/realtime.ts`, `src/server/realtime/*`, `RealtimeProvider`, tests)
- GPS live & tracking barber ; carte interactive (Leaflet derrière `MapProvider`)
- ETA dynamique (`distanceKm` / `estimateEtaMinutes` → `RoutingProvider`)
- Notifications temps réel (client & barber) — brancher `server/notifications.ts`,
  retirer `AutoRefresh`
- Paiement Stripe (architecture `Payment` prête) ; SMS ; emails
- Planning barber, disponibilités, avis clients, fidélité, promotions, factures
- Tableau de bord avancé

> Socles déjà présents : statut `EN_ROUTE`, `Barber.currentLat/Lng`,
> helpers ETA, `NEXT_PUBLIC_MAPS_PROVIDER`, transport temps réel (inerte tant
> que Supabase n'est pas configuré).

---

## 🏁 Phase 4 — Production & Scalabilité

Durcissement final. Sous-tâches internes indicatives :

- Sécurité (durcissement, secrets, rate limiting distribué)
- Optimisation & cache, performances production
- Monitoring / observabilité, alerting
- Tests (couverture élargie, e2e), CI/CD & DevOps
- Documentation, préparation à la montée en charge

---

## Politique de backlog

Toute idée hors de la phase en cours est **consignée ici** et **jamais
implémentée** avant la phase produit correspondante. La Phase 1 reste figée.
