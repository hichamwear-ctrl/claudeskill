# Backend Supabase — socle technique

Backend de l'application de services & livraisons à la demande, conforme au
document d'architecture technique v1.0.

> **Principe directeur :** la base de données est la source de vérité. Le schéma
> est versionné en migrations SQL (jamais de modification manuelle en prod, §18).

## Périmètre actuel

Seul le **socle technique** est en place. Les tables métier (missions,
commandes, services, livraisons, paiements...) sont **volontairement reportées**
tant que le PRD et la Spec UX ne sont pas finalisés.

| État | Élément |
|------|---------|
| ✅ | Structure Supabase versionnée (`config.toml`, `migrations/`) |
| ✅ | Extensions PostgreSQL (`postgis`, `pgcrypto`, `pg_net`, `pg_cron`, `uuid-ossp`) |
| ⏳ | Enums & rôles, RLS, hook JWT, auth — étapes suivantes |
| 🚫 | Tables métier — en attente du PRD / Spec UX |

## Prérequis

- Node ≥ 18 (CLI Supabase installée en devDependency)
- Docker (pour la stack locale `supabase start`)

## Commandes

```bash
npm install              # installe la CLI Supabase
npm run db:start         # démarre la stack Supabase locale (Docker)
npm run db:reset         # ré-applique toutes les migrations à neuf
npm run db:lint          # lint SQL des migrations
npm run migration:new    # crée un nouveau fichier de migration horodaté
npm run db:stop          # arrête la stack locale
```

## Organisation

```
supabase/
├── config.toml          # configuration du projet (API, Auth, DB, Realtime...)
├── migrations/          # migrations SQL versionnées, appliquées dans l'ordre
└── functions/           # Edge Functions (Deno) — à venir
```

## Secrets

Aucun secret n'est committé. Les clés (Twilio, Apple, Stripe...) sont fournies
via variables d'environnement — voir `.env.example`. En production elles vivent
dans Supabase Vault / la configuration d'environnement.
