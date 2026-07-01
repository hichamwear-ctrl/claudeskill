# Edge Functions

Fonctions serveur (Deno) pour toute la **logique sensible** : la clé `service_role` et les secrets
vivent ici, jamais dans l'app mobile (§4.5).

> État actuel : socle + **moteur conversationnel opérationnel** (M3 : `converse`,
> `submit-request`). Le moteur de dialogue est **pur** (`_shared/engine/`) ; l'IA
> (classification) est un **adaptateur remplaçable** (V1 : mots‑clés déterministe).

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
│   ├── handler.ts   # serve() : préflight + requestId + logs + gestion d'erreurs
│   ├── engine/      # MOTEUR PUR (M2.3) : compute() déterministe, évaluateur borné
│   │   ├── types.ts · conditions.ts · validate.ts · engine.ts · mod.ts
│   │   └── engine_test.ts
│   └── intake/      # ORCHESTRATION (M3) : tour de dialogue + clôture
│       ├── types.ts        # DTOs + interfaces IntakeStore / Classifier (seams)
│       ├── config.ts       # assemblage config + présentation + classifieur mots-clés
│       ├── orchestrator.ts # runTurn / finalize (dépend des interfaces → testable)
│       ├── store.ts        # IntakeStore concret (supabase-js, service_role)
│       └── *_test.ts        # tests hors-ligne (store en mémoire, fakes)
├── rpc.ts           # (dans _shared) mappe les erreurs SQLSTATE des RPC → HttpError
├── health/          # sonde runtime (publique)
├── converse/        # un tour du dialogue d'intake (auth)
├── submit-request/  # clôture de l'intake → mission pending_review (auth, M4)
├── review/          # revue opérateur : claim + décision (operator/admin, M4)
├── estimate-price/  # prix + ETA (auth, M4)
├── zone-check/      # couverture + horaires (auth, M4)
├── payments/        # adaptateur PSP : authorize/capture/void/refund (auth, M5)
└── send-push/       # transport des notifications (interne/webhook, M8)
```

> **Notifications (M8) :** `send-push` est un **transport pur** (mock Expo → FCM/
> APNS/email/SMS via `NOTIFY_TRANSPORT`). Toute la résolution data-driven
> (triggers → templates → `content_strings` → `notifications`, idempotence,
> silence nocturne, `min_interval`) est faite par la RPC `dispatch_notifications`
> — l'Edge ne contient **aucune logique métier**. Interface transport dans
> `_shared/notifications/`.

> **GPS (M7) :** **aucune Edge Function** non plus. Live = Broadcast ; émission de
> la dernière position = RPC `update_location` (refusée hors mission active) ;
> repli = RPC `get_operator_location`. `mission_tracks` (tracé persisté) est
> **différée** (pas d'historique GPS en V1). Sécurité Realtime durcie :
> `can_publish_topic` réserve la publication de `mission:{id}:location` à
> l'intervenant affecté.

> **Chat (M6) :** **aucune Edge Function** — le chat d'exécution est 100 % en base
> (table `messages` append-only, envoi par `INSERT` gardé par la RLS + trigger de
> modération déterministe, temps réel via Postgres Changes/Broadcast). L'accès aux
> canaux Realtime est autorisé par `can_access_topic` (policies `realtime.messages`).

> **Paiement (M5) :** l'interface métier `PaymentProvider` (mock→Stripe) vit dans
> `_shared/payments/` — le domaine ne dépend d'AUCUN PSP. Le paiement suit
> **intent → PSP → settle** : `payment_intent` (gate P1 en base), l'appel provider,
> puis `payment_settle` (service_role) qui enregistre + affecte la mission. Tous
> les invariants (jamais d'autorisation hors `accepted`, capture ≤ autorisé,
> preuve) sont **en SQL** ; l'Edge `payments` est un simple adaptateur. Provider
> choisi par `PAYMENT_PROVIDER=mock|stripe`.

> **Missions (M4) :** la logique sensible (machine à états, claim, prix, zone) vit
> dans des **RPC SQL SECURITY DEFINER** (`transition_mission`, `claim_review`,
> `create_mission_from_conversation`, `estimate_price`, `zone_check`) — testées
> directement contre PostgreSQL. Les Edge Functions `review`/`estimate-price`/
> `zone-check` sont de **fins wrappers** (auth + validation d'entrée + appel RPC +
> mapping d'erreurs). L'allow‑list de la machine à états est **en code** (table
> `mission_transitions` différée, LEAN_V1 §1.2).

> **Testabilité :** la logique vit derrière l'interface `IntakeStore` ; elle est
> testée hors‑ligne avec un store en mémoire. Le `SupabaseStore` (glue PostgREST)
> nécessiterait la stack complète pour un test E2E ; la **forme des requêtes** est
> validée séparément contre PostgreSQL (données/seed).

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
