# Gestion financière

Application web mobile-first de suivi financier : mois (revenus/dépenses, TVA, TVA
récupérée), capital global, journal Kharja par mois, et créances (« R »).

## Principes

- **Calculs fiables** : tous les montants sont manipulés en **centimes (entiers)**,
  jamais en flottant. Chaque calcul est une **fonction pure unique** (`src/core/finance`)
  couverte par des tests automatisés, réutilisée à l'identique côté serveur et client.
- **Trois totaux strictement séparés** : capital global (mois + Kharja), reste par mois,
  solde R — aucune fonction ne les mélange.
- **Sécurité serveur** : authentification par identifiants (mots de passe hachés Argon2id),
  sessions cookies `httpOnly`/`secure`/`sameSite=strict`, rôles vérifiés **sur chaque route
  API**, rate-limiting anti brute-force, en-têtes de sécurité (CSP, X-Frame-Options…).
- **Deux rôles** : `ADMIN` (lecture/écriture) et `READER` (lecture seule stricte, garantie
  côté backend).

## Stack

Next.js (App Router) · PostgreSQL · Prisma · Auth.js · Argon2 · @react-pdf/renderer · Vitest.

## Prérequis

- Node.js 20+
- Une base PostgreSQL accessible

## Configuration

La connexion est pilotée **uniquement** par `DATABASE_URL` : changer d'hébergeur ne
demande que de modifier cette variable.

```bash
cp .env.example .env
# puis renseigner DATABASE_URL, AUTH_SECRET (openssl rand -base64 32),
# et les comptes initiaux (SEED_*).
```

## Installation

```bash
npm install
npm run db:migrate   # applique la migration initiale
npm run db:seed      # catégories + base R (23 367,50 €) + comptes initiaux
```

## Développement

```bash
npm run dev          # http://localhost:3000
```

## Tests & vérifications

```bash
npm test             # tests unitaires des fonctions de calcul
npm run typecheck    # vérification des types
npm run build        # build de production
```

## Production

- HTTPS obligatoire.
- Renseigner les variables d'environnement (jamais commiter `.env`).
- `npm run build && npm run start`.

## Structure

```
src/
  core/finance/     Fonctions de calcul pures + tests (source unique)
  lib/              Prisma, auth, validation, requêtes composées, PDF
  app/api/          Routes serveur (rôles vérifiés à chaque endpoint)
  app/(app)/        Interface : onglets « Mois » et « R », détail mois, Kharja
  components/       Composants UI partagés
prisma/             Schéma, migration, seed
```
