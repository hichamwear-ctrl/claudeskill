# EXPO DEMO SETUP — Mise en service P0 — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** runbook opérationnel (backend **gelé**).
> **But :** rendre le backend M1→M12 **immédiatement utilisable** par une app Expo,
> en **mode mock** (aucun service externe). **Aucune modification du schéma.**
>
> **Pré‑requis :** Supabase CLI installé (`supabase --version`), un compte Supabase.
> **Cohérence :** `DEPLOYMENT.md` (checklist prod complète), `DEMO_READINESS.md` (audit).

---

## 1. Procédure de déploiement (projet Supabase vierge)

### Étape 0 — Créer le projet
Dashboard Supabase → **New project** → noter :
`PROJECT_REF`, **Database password**, `Project URL` (`https://<ref>.supabase.co`),
`anon key`, `service_role key` (Settings → API).

### Étape 1 — Lier le CLI au projet
```bash
supabase login
supabase link --project-ref <PROJECT_REF>      # demande le mot de passe DB
```

### Étape 2 — Activer les extensions
Dashboard → **Database → Extensions** → activer **`pg_net`** et **`pg_cron`**
(`postgis`, `pgcrypto`, `uuid-ossp` sont activés par la 1ʳᵉ migration).
> Les activer AVANT le push évite un échec sur `create extension pg_cron/pg_net`.

### Étape 3 — Appliquer les migrations (26)
```bash
supabase db push
```
Applique tout : extensions, hook JWT, storage, socle, moteur, missions, paiements,
chat, GPS, notifications, automatisation, admin, staging. Ordre garanti (timestamps).

### Étape 4 — Charger le seed (données de démo)
> `db push` **ne seede pas** le remote. Le seed est **idempotent** (`on conflict`).
```bash
# Option A — psql (chaîne de connexion Dashboard → Settings → Database)
psql "postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres" \
  -f supabase/seed.sql
# Option B — coller le contenu de supabase/seed.sql dans le SQL Editor
```
Contenu : 6 catégories, questions+options, tarif par défaut, **zone Bruxelles +
horaires**, textes i18n, catalogue de notifications, toutes les clés `app_config`.

### Étape 5 — Déployer les Edge Functions
```bash
supabase functions deploy          # déploie les 8 fonctions (verify_jwt lu de config.toml)
# (ou une par une : supabase functions deploy converse, ... )
```
Fonctions : `health` (publique), `converse`, `submit-request`, `review`,
`estimate-price`, `zone-check`, `payments`, `send-push`.

### Étape 6 — Activer le hook JWT (CRITIQUE)
Dashboard → **Authentication → Hooks → Custom Access Token** → choisir
**`public.custom_access_token_hook`** → **Enable**.
> Sans ça, aucun JWT ne porte `user_role` ⇒ **toute la RLS retombe sur `client`**.
> (Le `config.toml [auth.hook.custom_access_token]` ne vaut qu'en local.)

### Étape 7 — Activer une méthode de connexion
Dashboard → **Authentication → Providers** :
- **Email** (déjà actif) → suffisant pour la démo (OTP/magic link/mot de passe).
- **Phone (Twilio)** / **Apple** = P1 (login « device » réel), non requis en démo.

---

## 2. Variables d'environnement & secrets (démo mock = AUCUN externe)

| Variable | Où | Démo | Valeur |
|---|---|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | injectées aux Edge Functions | auto | — |
| `PAYMENT_PROVIDER` | secret Edge (optionnel) | **mock** (défaut) | `mock` |
| `NOTIFY_TRANSPORT` | secret Edge (optionnel) | **mock** (défaut) | `mock` |
| `CORS_ALLOW_ORIGIN` | secret Edge (optionnel) | `*` (défaut) | — |
| `app_config.notifications.push_enabled` | base (seed) | **false** | pas de push externe |

```bash
# Optionnel (les défauts suffisent) — figer explicitement le mode mock :
supabase secrets set PAYMENT_PROVIDER=mock NOTIFY_TRANSPORT=mock
```
> **Aucun** Twilio / Apple / Expo / Stripe requis pour la démo.

**Côté app Expo**, seules deux valeurs suffisent :
`EXPO_PUBLIC_SUPABASE_URL = <Project URL>` et `EXPO_PUBLIC_SUPABASE_ANON_KEY = <anon key>`.

---

## 3. SQL de bootstrap — comptes de démo (sans contourner les règles)

> On **crée de vrais utilisateurs Auth** (l'app‑trigger crée le profil en `client`),
> puis on **promeut** les rôles par SQL direct (contexte serveur, sans JWT) — c'est
> l'amorçage prévu (la garde anti‑escalade n'autorise le changement de rôle qu'à un
> admin **ou** en contexte serveur de confiance).

### 3.1 Créer les 3 comptes (Auth Admin API)
```bash
SUPABASE_URL="https://<PROJECT_REF>.supabase.co"
SR="<service_role key>"
for u in client operator admin; do
  curl -s -X POST "$SUPABASE_URL/auth/v1/admin/users" \
    -H "apikey: $SR" -H "Authorization: Bearer $SR" -H "Content-Type: application/json" \
    -d "{\"email\":\"$u@demo.test\",\"password\":\"Demo1234!\",\"email_confirm\":true}" >/dev/null
done
```
*(Alternative : Dashboard → Authentication → Add user, `email_confirm` coché.)*

### 3.2 Promouvoir les rôles (SQL Editor)
```sql
-- Le profil est créé automatiquement en 'client' à l'inscription.
update public.profiles set role = 'admin'    where email = 'admin@demo.test';
update public.profiles set role = 'operator' where email = 'operator@demo.test';
-- client@demo.test reste 'client' (défaut) — rien à faire.
select email, role from public.profiles where email like '%@demo.test';
```
> ⚠️ Après promotion, l'opérateur/l'admin doit **se reconnecter** (nouveau token)
> pour que le claim `user_role` soit ré‑émis par le hook.

---

## 4. Vérifier le hook JWT (`user_role`)

### 4.1 Côté base (SQL Editor) — teste la logique du hook directement
```sql
select public.custom_access_token_hook(
  jsonb_build_object(
    'user_id', (select id from auth.users where email = 'operator@demo.test'),
    'claims',  '{}'::jsonb
  )
) -> 'claims' ->> 'user_role';        -- attendu : operator
```
*(Profil inexistant ⇒ défaut `client` — comportement robuste vérifié.)*

### 4.2 Côté app — après connexion en tant qu'opérateur
- Décoder l'`access_token` (jwt.io) → doit contenir `"user_role": "operator"`.
- **ou** appeler la RPC `operator_queue()` → retourne `[]` (et **non** `403 réservé aux opérateurs`).

---

## 5. Vérifier le parcours 100 % mock (aucun service externe)

- **Paiement** : l'Edge `payments` utilise `getProvider()` → `PAYMENT_PROVIDER`
  (défaut **mock**) : `authorize/capture/void/refund` simulés (réfs `sim_pi_…`),
  aucun appel Stripe. Le montant capturé est **replafonné en base** (garde‑fou).
- **Notifications** : écrites en base par trigger (in‑app immédiat, idempotent) ;
  la livraison push est **désactivée** (`push_enabled=false`) → le trigger est
  **neutre** (aucun appel réseau). `NOTIFY_TRANSPORT` = mock si jamais activé.
- **Conclusion** : le parcours **submit → review → paiement → exécution → chat →
  GPS → clôture → notifications in‑app** fonctionne **sans Twilio/Apple/Expo/Stripe**.

Test rapide (SQL Editor, en admin) après seed :
```sql
select public.validate_config();     -- attendu : []  (configuration cohérente)
```
Test de connectivité Edge :
```bash
curl -s "$SUPABASE_URL/functions/v1/health"     # { "data": { "status": "ok", ... } }
```

---

## 6. ✅ Checklist finale « Backend prêt pour Expo »

**Déploiement**
- [ ] `supabase link` OK
- [ ] `pg_net` + `pg_cron` activés (Dashboard)
- [ ] `supabase db push` : 26 migrations sans erreur
- [ ] Seed chargé (`select count(*) from service_categories;` = 6)
- [ ] `supabase functions deploy` : 8 fonctions déployées
- [ ] `curl …/functions/v1/health` → `{ "data": { "status": "ok" } }`

**Auth & rôles**
- [ ] Hook **Custom Access Token** activé (Dashboard) → `public.custom_access_token_hook`
- [ ] Provider **Email** actif (login démo)
- [ ] 3 comptes créés (`client@`, `operator@`, `admin@` `demo.test`)
- [ ] Rôles promus (`select role from profiles where email like '%@demo.test'`)
- [ ] Login opérateur → JWT contient `user_role=operator` (ou `operator_queue()` ≠ 403)

**Mode mock**
- [ ] `PAYMENT_PROVIDER=mock`, `NOTIFY_TRANSPORT=mock` (défauts)
- [ ] `notifications.push_enabled = false`
- [ ] `select public.validate_config();` → `[]`

**Contrats mobile**
- [ ] URL + anon key transmis à l'app (`EXPO_PUBLIC_SUPABASE_*`)
- [ ] Enveloppes vérifiées : succès `{ "data": … }`, erreur `{ "error": { message, code } }`

**Smoke test métier (via l'app ou l'API, comptes de démo)**
- [ ] Client : `converse` → questions → `submit-request` → mission `pending_review`
- [ ] Opérateur : `operator_queue` → `review` (claim + accept)
- [ ] Client : `payments` (authorize, mock) → mission `assigned`
- [ ] Opérateur : `transition_mission` (shopping→…→in_progress), chat, `update_location`
- [ ] Opérateur : `payments` (capture, mock) → mission `completed`
- [ ] Client : notifications in‑app présentes ; `mission_overview` complet

> **Toutes cases cochées ⇒ le backend est prêt : démarrer le frontend Expo.**
