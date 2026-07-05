# Barber Home — Le Uber des barbers à domicile 💈

Plateforme SaaS complète de réservation de barbers à domicile à Bruxelles :
réservation multi-personnes, suivi **temps réel + GPS**, paiement, fidélité,
favoris, dashboards Client / Barber / Admin. Thème sombre premium, mobile-first.

> **Prêt à l'emploi immédiatement** : sans aucune clé d'API, l'application tourne
> de bout en bout grâce à des fournisseurs *mock* (paiement, email, SMS, temps
> réel, carte). Renseignez les clés réelles quand vous le souhaitez — voir
> [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

## Stack

Next.js 15 (App Router) · React 19 · TypeScript strict · TailwindCSS ·
Framer Motion · Prisma · PostgreSQL · Auth.js (NextAuth v5) · Zod ·
TanStack Query · Zustand · Supabase Realtime (temps réel) · Stripe (paiement) ·
pdf-lib (factures) · Vitest (tests).

---

## 🚀 Démarrage rapide (local)

```bash
cp .env.example .env      # les valeurs par défaut suffisent en local
npm install
npm run db:push           # crée le schéma dans PostgreSQL
npm run db:seed           # comptes + données de démonstration
npm run dev               # http://localhost:3000
```

Il vous faut simplement une base **PostgreSQL** accessible et renseignée dans
`DATABASE_URL` (`.env`). Rien d'autre n'est requis pour tester.

### Comptes de démonstration (créés par `db:seed`)

| Rôle   | Email                     | Mot de passe |
| ------ | ------------------------- | ------------ |
| Client | `client@barberhome.be`    | `password123` |
| Barber | `karim@barberhome.be`     | `password123` |
| Admin  | `admin@barberhome.be`     | `password123` |

Le seed crée aussi une réservation **en cours** et une réservation **terminée**
(avec facture, avis et points de fidélité) pour que chaque dashboard soit déjà
peuplé.

---

## ⚙️ Configuration des variables d'environnement

Tout est documenté dans `.env.example`. Les 3 seules variables nécessaires en
local/production : `DATABASE_URL`, `AUTH_SECRET`, `AUTH_URL`. Les autres activent
les intégrations réelles ; laissées vides, le mode mock s'applique.

---

## 🧪 Tester chaque rôle

### Client (`client@barberhome.be`)
1. **Réserver** : `Nouvelle réservation` → adresse (ou géolocalisation) → créneau
   → personnes & prestations → détails d'accès → résumé → confirmer.
2. **Suivi temps réel** : quand le barber passe `EN_ROUTE`, la carte de suivi et
   l'ETA s'affichent sur le tableau de bord.
3. **Paiement** : choisir *En ligne* → page **Paiements** → `Payer en ligne`
   (réglé instantanément par le mock).
4. **Factures** : historique → `Facture PDF` (PDF réel).
5. **Fidélité** : page **Fidélité** → voir points/niveau → échanger un bon.
6. **Favoris** : cœur sur une prestation terminée → page **Favoris** → re-réserver.

### Barber (`karim@barberhome.be`)
1. **Disponibilités** : horaires hebdomadaires + congés/indisponibilités par date.
2. **Missions** : accepter une demande, puis faire évoluer le statut
   (`En route` → `Arrivé` → `En cours` → `Terminé`).
3. **GPS** : en `EN_ROUTE`, le partage de position s'active (le navigateur
   demande l'autorisation de géolocalisation).
4. **Revenus / historique / planning** : onglets dédiés.

### Admin (`admin@barberhome.be`)
Vue d'ensemble (CA, réservations, clients, barbers, graphiques) + gestion des
réservations (changement de statut), barbers, clients, avis et promotions.

---

## 💳 Paiements mock (par défaut)

Sans `STRIPE_SECRET_KEY`, un fournisseur *mock* règle le paiement en ligne
instantanément (statut `PAID`) et émet la facture — **aucune transaction
réelle**. Idéal pour tester le parcours complet.
Pour Stripe réel : voir [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

## 🔌 Remplacer les fournisseurs mock par les services réels

Chaque intégration est derrière une interface propre avec un adaptateur mock par
défaut. Il suffit de renseigner les variables `.env` (et, pour email/SMS,
d'implémenter l'adaptateur) — **aucun composant ni route à modifier**.

| Intégration | Variable(s) | Détails |
|---|---|---|
| Temps réel | `NEXT_PUBLIC_SUPABASE_*`, `SUPABASE_SERVICE_ROLE_KEY` | Supabase Realtime |
| Paiement | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Stripe Checkout + webhook |
| Email | `RESEND_API_KEY` | `setEmailProvider(...)` |
| SMS | `TWILIO_*` | `setSmsProvider(...)` |
| Carte | `NEXT_PUBLIC_MAPS_PROVIDER`, `NEXT_PUBLIC_GOOGLE_MAPS_KEY` | Leaflet/Google |
| Monitoring | `SENTRY_DSN` | `@sentry/nextjs` |

Guide complet : [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

---

## 📦 Scripts

| Commande | Rôle |
|---|---|
| `npm run dev` | Développement |
| `npm run build` / `npm run start` | Build / serveur de production |
| `npm run verify` | lint + typecheck + test + build |
| `npm run lint` · `typecheck` · `test` | Qualité (individuel) |
| `npm run db:push` · `db:seed` · `db:studio` | Schéma / données / inspection |
| `npm run db:migrate` · `db:migrate:dev` · `db:reset` | Migrations (prod/dev) |

## 🗂️ Structure

```
src/
├── app/                     # App Router : (auth) · (client) · (barber) · (admin) · api
├── components/              # ui/ · marketing/ · dashboard/ · booking/ · tracking/ · map/ · realtime/
├── server/                  # code SERVEUR only : prisma, auth, api, reservations, barber,
│                            #   admin, loyalty, invoices, notifications/, payments/, realtime/, monitoring
├── lib/                     # logique PURE partagée : pricing, zones, routing, loyalty,
│                            #   working-hours, unavailability, geo-project, realtime, utils…
├── hooks/                   # useRealtime, useReservationChannel, useBarberGeolocation
└── stores/                  # Zustand (assistant de réservation)
prisma/                      # schema.prisma + seed.ts
docs/                        # INTEGRATIONS.md · DEPLOYMENT.md
```

`src/server/*` n'est jamais importé côté client (frontière stricte, vérifiée).

## 🔒 Sécurité

Sessions JWT · middleware RBAC par rôle · **validation Zod** sur toutes les
entrées · **bcrypt** (coût 12) · **rate limiting** sur les endpoints sensibles ·
tokens de canal temps réel **signés (HMAC)** · webhook Stripe à **signature
vérifiée** · **en-têtes de sécurité** (HSTS, X-Frame-Options, nosniff,
Referrer-Policy, Permissions-Policy) · erreurs jamais divulguées au client.

## 🚀 Déploiement

Guide complet (Vercel, PostgreSQL, migrations, sauvegarde/restauration,
monitoring, checklist) : [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## ✅ Qualité

`npm run verify` doit être au vert (lint · typecheck · test · build). La CI
GitHub Actions exécute ces mêmes contrôles sur chaque push / PR.
