# Application mobile Expo — `[NOM_PRODUIT]`

App React Native / Expo (Client + Intervenant, une base de code). Consomme le
**backend gelé** (Supabase) décrit dans `../docs/`. Architecture de référence :
`../docs/MOBILE_ARCHITECTURE.md`.

> **État : MOBILE 1 — Socle technique.** Aucun écran métier. Le socle est
> compilable (`tsc`), testé (`jest`) et prêt à accueillir les futurs modules.

## Prérequis & démarrage

```bash
cp .env.example .env          # renseigner l'URL + anon key (docs/EXPO_DEMO_SETUP.md §2)
npm install
npm start                     # Expo Dev Server (QR code / simulateur)
```

## Scripts

| Script | Rôle |
|---|---|
| `npm start` | serveur de dev Expo |
| `npm run typecheck` | TypeScript strict (`tsc --noEmit`) |
| `npm run lint` | ESLint (config Expo) |
| `npm test` | Jest (`jest-expo`) |
| `npm run format` | Prettier |
| `npm run gen:types` | régénère `src/types/database.types.ts` (Supabase, env avec stack) |

## Ce que contient le socle (MOBILE 1)

- **Config** : `app.config.ts` (scheme deep-link, plugins, permissions FR),
  `babel/metro/eslint/prettier/jest`, `tsconfig` strict + alias `@/*`.
- **Supabase** : client unique typé (`anon` + JWT), session en **SecureStore**
  (chunké), rafraîchissement lié à l'`AppState`.
- **Appels API** : `callEdge` (enveloppe `{data}`/`{error}`, `Idempotency-Key`,
  `X-Api-Version`), `callRpc` (SQLSTATE → `AppError`), `unwrap` (PostgREST).
- **Realtime** : `RealtimeManager` (canaux privés, comptage de références,
  `setRealtimeAuth`) + hook `useRealtimeChannel`.
- **Cache/offline** : React Query + persistance AsyncStorage, `onlineManager`
  (NetInfo) + `focusManager`.
- **État** : stores Zustand (`session`, `connectivity`, `ui`).
- **Design System maison** : tokens + thème clair (dark-ready), primitives
  `Screen`/`Text`/`Button`.
- **i18n** : i18next (couche shell `locales/fr.json`).
- **Types** : `database.types.ts` (dérivé du schéma gelé), helpers `Tables`/`Enums`.
- **Écran de diagnostic** : `app://health` — vérifie la communication avec le
  backend (Edge `health`) et illustre les 4 états d'écran.

## Conventions

Voir `../docs/MOBILE_ARCHITECTURE.md` §3 (nommage, TypeScript, style). En bref :
composants `PascalCase` (export nommé), hooks `useXxx`, alias `@/*`, aucun `any`,
enums de statut issus des types générés, `AppError` unique forme d'erreur,
`écran → hook de feature → api de feature → service`.
