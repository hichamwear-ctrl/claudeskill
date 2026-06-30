# Edge Functions

Fonctions serveur (Deno) pour toute la **logique sensible** : la clé `service_role` et les secrets
vivent ici, jamais dans l'app mobile (§4.5).

> État actuel : **squelette uniquement**. Aucune logique métier. Seule la fonction d'exemple
> `health` est présente.

## Organisation

```
functions/
├── deno.json        # import map (@supabase/supabase-js), config fmt/lint
├── _shared/         # code partagé (préfixe _ : non déployé comme fonction)
│   ├── env.ts       # variables d'environnement (lecture + validation)
│   ├── cors.ts      # en-têtes CORS + préflight OPTIONS
│   ├── errors.ts    # HttpError (statut + code) + raccourcis
│   ├── http.ts      # réponses JSON normalisées (ok / error)
│   ├── logger.ts    # journalisation structurée (JSON + requestId)
│   ├── supabase.ts  # clients Supabase (utilisateur RLS / admin service_role)
│   ├── auth.ts      # requireUser / requireRole (rôle via claim JWT)
│   └── handler.ts   # serve() : préflight + requestId + logs + gestion d'erreurs
└── health/          # fonction d'exemple (sonde runtime, publique)
    └── index.ts
```

## Conventions

- Une fonction = un dossier `nom-fonction/index.ts` qui appelle `serve()`.
- Toujours passer par `serve()` (du `_shared/handler.ts`) : il gère CORS, corrélation (`requestId`),
  logs et conversion des erreurs.
- Réponses via `ok()` / `error()` ; erreurs métier via `HttpError`.
- Accès données : `createUserClient(req)` (soumis à la RLS) par défaut ; `createAdminClient()`
  (service_role) seulement pour les opérations serveur.
- `verify_jwt = true` par défaut ; n'ouvrir en public (`config.toml`) que les sondes et les webhooks
  à signature (ex. Stripe).

### Ajouter une fonction

```ts
// functions/send-push/index.ts
import { serve } from '../_shared/handler.ts';
import { ok } from '../_shared/http.ts';
import { createAdminClient } from '../_shared/supabase.ts';

serve('send-push', async (req, { log }) => {
  // ... logique ...
  return ok({ sent: true });
});
```

Cette base est prête à accueillir, sans refonte : **notifications push**, **Stripe** (PaymentIntent,
webhook signé), **calculs serveur**, **SMS**, **emails**, **géolocalisation** et **traitements
planifiés (cron)** — chaque cas devient une nouvelle fonction réutilisant `_shared/`.

## Développement local

```bash
# Type-check + lint de toutes les fonctions
deno check supabase/functions/**/index.ts
deno lint  supabase/functions

# Servir localement (nécessite la stack Supabase via Docker)
npm run functions:serve
```

## Secrets

Fournis au runtime via `supabase secrets set` (jamais committés). Les variables `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` sont injectées automatiquement par la plateforme.
