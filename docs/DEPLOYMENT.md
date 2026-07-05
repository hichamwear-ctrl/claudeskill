# Déploiement, maintenance & exploitation

Guide production pour Barber Home (Next.js 15 · Prisma · PostgreSQL).

## 1. Prérequis

- Node.js **22+**
- Une base **PostgreSQL** (Neon, Supabase, RDS, Railway…)
- (Optionnel) comptes Stripe, Supabase, Resend/Twilio, Sentry — voir
  [`INTEGRATIONS.md`](./INTEGRATIONS.md). Sans clés, l'app tourne en mode mock.

## 2. Variables d'environnement

Toutes documentées dans `.env.example`. Obligatoires en production :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Chaîne PostgreSQL |
| `AUTH_SECRET` | Secret de session (générer : `openssl rand -base64 32`) |
| `AUTH_URL` | URL publique (https en prod → cookies sécurisés automatiques) |

Les autres activent les intégrations réelles quand renseignées (sinon mock).

## 3. Base de données

- **Développement** : `npm run db:push` (sync direct du schéma) puis `npm run db:seed`.
- **Production** : utiliser des migrations versionnées.
  ```bash
  npm run db:migrate:dev   # créer une migration en local
  npm run db:migrate       # appliquer (prisma migrate deploy) en CI/CD ou au boot
  ```
- `npm run db:studio` pour inspecter, `npm run db:reset` pour repartir de zéro (dev).

## 4. Déploiement Vercel

1. Importer le repo dans Vercel.
2. Renseigner les variables d'environnement (section 2).
3. Build command : `npm run build` (exécute `prisma generate`).
4. Étape de release / post-deploy : `npm run db:migrate`.
5. Region : proche de la base (ex. `fra1` pour l'Europe).

En-têtes de sécurité (HSTS, X-Frame-Options, nosniff, Referrer-Policy,
Permissions-Policy) sont servis via `next.config.ts`.

### Temps réel en serverless
Le transport temps réel est **Supabase Realtime** (managé) — aucun serveur
WebSocket à héberger. Renseigner les variables `NEXT_PUBLIC_SUPABASE_*` +
`SUPABASE_SERVICE_ROLE_KEY` pour l'activer.

## 5. Monitoring & erreurs

- Logs structurés via `src/lib/logger.ts` (niveau : `LOG_LEVEL`).
- Toutes les erreurs API passent par `captureError` (`src/server/monitoring.ts`).
- **Activer Sentry** : `npm i @sentry/nextjs`, définir `SENTRY_DSN` /
  `NEXT_PUBLIC_SENTRY_DSN`, décommenter l'appel `Sentry.captureException` dans
  `src/server/monitoring.ts`. Aucun autre changement requis.

## 6. Sauvegarde & restauration

```bash
# Sauvegarde
pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%F).dump

# Restauration
pg_restore --clean --no-owner -d "$DATABASE_URL" backup_YYYY-MM-DD.dump
```
Recommandé : snapshots automatiques du fournisseur managé + un `pg_dump`
quotidien conservé hors-site. Tester la restauration régulièrement.

## 7. CI/CD

`.github/workflows/ci.yml` exécute, sur chaque push / PR :
`npm ci` → `lint` → `typecheck` → `test` → `build`.
Ajouter un job de déploiement (ou laisser l'intégration Vercel) et une étape
`npm run db:migrate` avant la mise en ligne.

## 8. Checklist de mise en production

- [ ] `AUTH_SECRET` fort, `AUTH_URL` en https
- [ ] `DATABASE_URL` sur une base managée avec sauvegardes
- [ ] Migrations appliquées (`db:migrate`)
- [ ] Clés réelles renseignées pour les intégrations souhaitées
- [ ] Webhook Stripe pointé sur `/api/payments/webhook`
- [ ] Sentry activé (optionnel)
- [ ] `npm run verify` au vert
