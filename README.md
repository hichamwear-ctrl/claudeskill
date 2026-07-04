# Barber Home — Le Uber des barbers à domicile 💈

Plateforme SaaS premium de réservation de barbers à domicile à Bruxelles.
Design haut de gamme (noir profond · doré · anthracite), dark theme, mobile-first.

## Stack

- **Next.js 15** (App Router) · **React 19** · **TypeScript** (strict)
- **TailwindCSS** + composants type shadcn/ui (Radix)
- **Framer Motion** (animations premium)
- **Prisma** + **PostgreSQL**
- **Auth.js / NextAuth v5** (credentials, JWT, rôles)
- **React Hook Form** + **Zod** (validation)
- **TanStack Query** · **Zustand** (état du booking)
- Architecture prête pour **Stripe**, notifications temps réel et carte (Leaflet/Google Maps)

## Fonctionnalités

### 3 rôles, 3 dashboards
- **CLIENT** — tableau de bord, réservation multi-étapes, historique, factures, adresses, profil
- **BARBER** — demandes entrantes, courses en cours, planning, revenus, disponibilité, changement de statut
- **ADMIN** — statistiques, graphiques, gestion réservations / barbers / clients / avis / promotions

### Workflow de réservation (5 étapes)
1. **Adresse** — géolocalisation ou saisie ; détection auto de la zone Bruxelles (supplément déplacement hors zone)
2. **Date & heure** — créneaux disponibles uniquement
3. **Personnes** — adultes/enfants illimités, chacun avec sa prestation ; calcul auto durée + prix
4. **Détails d'accès** — digicode, étage, parking, notes
5. **Résumé** — récapitulatif complet + mode de paiement + confirmation

### Statuts de réservation (temps réel)
`DEMANDE_ENVOYEE → ACCEPTEE → BARBER_ATTRIBUE → EN_ROUTE → ARRIVE → EN_COURS → TERMINEE` (+ `ANNULEE`)
Le dashboard client se met à jour automatiquement (stand-in temps réel via revalidation, prêt pour Socket.io/Supabase).

## Démarrage

```bash
# 1. Dépendances
npm install

# 2. Configuration
cp .env.example .env
#   → renseignez DATABASE_URL (PostgreSQL) et AUTH_SECRET

# 3. Base de données
npm run db:push      # applique le schéma Prisma
npm run db:seed      # données de démo (admin, barbers, client, promos)

# 4. Développement
npm run dev          # http://localhost:3000
```

### Comptes de démo (après `db:seed`)

| Rôle   | Email                     | Mot de passe |
| ------ | ------------------------- | ------------ |
| Admin  | admin@barberhome.be       | password123  |
| Barber | karim@barberhome.be       | password123  |
| Client | client@barberhome.be      | password123  |

## Structure

```
src/
├── app/
│   ├── (auth)/              # login, register, forgot-password
│   ├── (client)/client/     # dashboard client + booking + historique + adresses + profil
│   ├── (barber)/barber/     # dashboard barber + planning + revenus + historique
│   ├── (admin)/admin/       # dashboard admin + gestion
│   ├── api/                 # routes REST (auth, reservations, reviews, addresses, profile, invoices…)
│   ├── layout.tsx · page.tsx (landing) · robots.ts · sitemap.ts
├── components/
│   ├── ui/                  # primitives (button, card, input, tabs, toast…)
│   ├── marketing/           # header, hero, sections, footer
│   ├── auth/ · booking/ · dashboard/
├── lib/                     # prisma, auth, pricing, zones, status, validations, notifications, api…
├── stores/                  # Zustand (booking wizard)
└── types/                   # augmentation des types NextAuth
```

## Sécurité

- Validation **Zod** sur toutes les entrées API
- Hash des mots de passe **bcrypt** (coût 12)
- **Middleware** de protection des routes par rôle
- **Rate limiting** en mémoire (à remplacer par Redis en prod)
- Réponses constantes sur « mot de passe oublié » (anti-énumération)
- Calcul des prix **côté serveur** (jamais de confiance dans le total client)

## Prochaines étapes (extensible)

- Intégration **Stripe** (architecture Payment déjà en place)
- Notifications **email/SMS** réelles (Resend, Twilio) via `lib/notifications.ts`
- **Temps réel** Socket.io / Supabase (remplacer `AutoRefresh`)
- **Carte** live barber + ETA (helpers `distanceKm` / `estimateEtaMinutes` prêts)
- Génération **PDF** serveur des factures (actuellement HTML imprimable)
- Application **mobile** (API REST déjà exposée)
