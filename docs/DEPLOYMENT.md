# DEPLOYMENT — Staging & Production — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** checklist de mise en service (M12)
> **Nature :** guide opérationnel pour déployer le backend (M1→M11) sur Supabase.
> **Rien de métier ici** — uniquement l'infrastructure et sa configuration.
>
> **Cohérence :** `Architecture_Technique.md`, `API_SPEC.md`, `NOTIFICATIONS.md`,
> `GPS_TRACKING.md`, `CHAT.md`, `LEAN_V1.md`.

---

## 1. Ce qui est câblé par le code (migrations `supabase/`)

| Domaine | Câblage | Migration / fichier |
|---|---|---|
| **Extensions** | `postgis`, `pgcrypto`, `uuid-ossp`, **`pg_net`**, **`pg_cron`** | `…_extensions.sql` |
| **Auth hook** | `custom_access_token_hook` → claim `user_role` | `…_auth_access_token_hook.sql` + `config.toml [auth.hook.custom_access_token]` |
| **Storage** | 4 buckets **privés** + policies propriétaire ; **mission-proofs = participants** | `…_storage_buckets.sql` + `…_staging_wiring.sql` |
| **Realtime (autz)** | `can_access_topic` / `can_publish_topic` + policies `realtime.messages` | `…_realtime_authorization.sql`, `…_realtime_publish.sql` |
| **Realtime (Changes)** | publication `supabase_realtime` : `messages`, `missions`, `mission_events`, `notifications` | `…_staging_wiring.sql` (gardé) |
| **Notifications (écriture)** | triggers `mission_events`/`messages`/`payments` → `dispatch_notifications` (idempotent) | `…_event_notifications.sql` |
| **Notifications (push)** | trigger `notifications` → `net.http_post` → `send-push` (transport Expo) | `…_staging_wiring.sql` (gardé par `app_config`) |
| **pg_cron** | expirations + purges (6 jobs) | `…_maintenance.sql` (gardé) |
| **Edge Functions** | `health`, `converse`, `submit-request`, `review`, `estimate-price`, `zone-check`, `payments`, `send-push` | `config.toml [functions.*]` |

> **Gardes** : les blocs dépendants de `pg_net`/`pg_cron`/schéma `realtime`/`storage`
> sont **conditionnels** → neutres en local, actifs sur Supabase. Rien à modifier.

---

## 2. Secrets requis (AUCUN n'est en dur — tous via env / Vault)

| Secret | Où | Usage | Requis |
|---|---|---|---|
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | injectés par la plateforme aux Edge Functions | clients Supabase | **oui** (auto) |
| `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN` | env projet | OTP téléphone (prod) | oui (SMS) |
| `SUPABASE_AUTH_EXTERNAL_APPLE_SECRET` | env projet | Sign in with Apple | oui (iOS) |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET` | env projet | Google (V2) | non (V2) |
| `PAYMENT_PROVIDER` | secret Edge (`supabase secrets set`) | `mock` \| `stripe` | oui (`mock` en staging) |
| `NOTIFY_TRANSPORT` | secret Edge | `mock` \| `expo` \| `fcm` | oui (`mock`/`expo`) |
| `NOTIFY_WEBHOOK_SECRET` | secret Edge **+** `app_config.notifications.webhook_secret` (idéalement **Vault**) | verrou d'appel de `send-push` | oui (si push réel) |
| *(futur)* `EXPO_ACCESS_TOKEN` | secret Edge | transport Expo réel | V-push |
| *(futur)* `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | secret Edge | provider Stripe | V-Stripe |

> **Config runtime (base, non secrète)** — `app_config` (admin) : `notifications.push_enabled`
> (`true` pour activer le push), `notifications.send_push_url` (URL de `send-push`).
> Le **secret** de webhook doit venir de **Vault** en production (pas d'`app_config`).

---

## 3. Activer le push réel en staging (4 étapes)

1. Déployer les Edge Functions ; noter l'URL de `send-push`
   (`https://<ref>.supabase.co/functions/v1/send-push`).
2. `supabase secrets set NOTIFY_WEBHOOK_SECRET=… NOTIFY_TRANSPORT=expo`.
3. `app_config` : `notifications.send_push_url = "<url>"`,
   `notifications.push_enabled = true`, `notifications.webhook_secret = "<secret>"`
   (ou Vault `notify_webhook_secret`).
4. Vérifier : une transition (`accepted`) crée une `notifications` → le trigger
   appelle `send-push?notification_id=…` → push Expo, `delivered_at` posé.

> **Local / staging sans push** : `push_enabled=false` (défaut) → in-app seulement,
> aucun appel externe (comportement testé).

---

## 4. Canaux Realtime (privés, autorisés)

| Canal | Type | Lecture (`can_access_topic`) | Écriture (`can_publish_topic`) |
|---|---|---|---|
| `mission:{id}:chat` | Postgres Changes | participant | participant (via table) |
| `mission:{id}:typing` | Broadcast | participant | participant |
| `mission:{id}:location` | Broadcast | participant | **intervenant affecté seul** |
| `mission:{id}:status` | Postgres Changes | participant | **serveur seul** |
| `operator:review-inbox` | Postgres Changes | operator/admin | serveur seul |

> Aucun abonnement inter-missions possible ; topic inconnu/malformé → **DENY**.

---

## 5. ✅ Checklist Production / Staging

**Base de données & migrations**
- [ ] `supabase db push` (23 migrations) sans erreur
- [ ] `supabase db reset` rejoue migrations **+ seed** proprement
- [ ] Extensions actives : `postgis`, `pg_net`, `pg_cron`, `pgcrypto`
- [ ] `pg_cron` : 6 jobs planifiés (`select * from cron.job`)
- [ ] Publication `supabase_realtime` contient `messages`, `missions`, `mission_events`, `notifications`

**Auth**
- [ ] Hook `custom_access_token` **enabled** ; un JWT de test contient `user_role`
- [ ] OTP téléphone (Twilio) : `account_sid` + `message_service_sid` + token (env)
- [ ] Sign in with Apple : Service ID (`client_id`) + secret (env) ; `enabled = true`
- [ ] `site_url` / `additional_redirect_urls` = domaines de l'app
- [ ] Rate limits OTP/sign-in adaptés

**Storage**
- [ ] 4 buckets **privés** créés (`avatars`, `request-photos`, `mission-proofs`, `documents`)
- [ ] Aucune lecture **publique** (tous `public = false`)
- [ ] Policies : propriétaire (avatars/request-photos/documents), **participant** (mission-proofs), admin
- [ ] Tailles max + MIME appliqués ; accès par **URL signées** uniquement

**Realtime**
- [ ] Policies `realtime.messages` présentes (read = `can_access_topic`, write = `can_publish_topic`)
- [ ] Test : un tiers ne peut ni s'abonner ni publier sur `mission:{autre}`
- [ ] Test : un client ne peut PAS publier `:location` ni `:status`

**Edge Functions**
- [ ] 8 fonctions déployées ; `verify_jwt` correct (`send-push` = false ; autres = true)
- [ ] Secrets Edge posés (`PAYMENT_PROVIDER`, `NOTIFY_TRANSPORT`, `NOTIFY_WEBHOOK_SECRET`)
- [ ] CORS : origines de l'app autorisées (`_shared/cors.ts`)
- [ ] Logs structurés visibles (requestId) ; erreurs 4xx/5xx propres

**Notifications / push**
- [ ] `notifications.push_enabled = true` + `send_push_url` + secret (Vault)
- [ ] Transport réel (`NOTIFY_TRANSPORT=expo`) + `EXPO_ACCESS_TOKEN`
- [ ] Test bout en bout : transition → notif in-app → push reçu + `delivered_at`
- [ ] Catalogue `notification_templates`/`triggers` + `content_strings` vérifiés (`validate_config()`)

**Plateforme / exploitation**
- [ ] SMTP (emails auth) configuré
- [ ] DNS / domaine / **SSL** (auto Supabase) ; domaine custom si besoin
- [ ] **Monitoring** (Supabase Logs/Reports) + **alerting** (file de revue, erreurs)
- [ ] **Sauvegardes** activées (PITR selon plan) + test de restauration
- [ ] **Rotation des clés** (JWT signing, service_role) planifiée
- [ ] **Rate limiting** applicatif (auth déjà borné ; envisager sur Edge sensibles)
- [ ] **CSP**/headers côté app ; secrets **jamais** exposés au client
- [ ] `app_config` de prod revu (seuils, `feature.*`, `gps.*`, `chat.*`, `notifications.*`)
- [ ] `validate_config()` = `[]` (aucune incohérence de configuration)

---

## 6. Validation « prête pour le mobile »

Le backend est **prêt à recevoir une app Expo en staging** dès que la section 5
« Base de données », « Auth », « Storage », « Realtime », « Edge Functions » est
cochée. Le **push réel** et **Stripe** sont activables ensuite par configuration,
sans changement de code (interfaces `PaymentProvider` / `PushTransport`).
