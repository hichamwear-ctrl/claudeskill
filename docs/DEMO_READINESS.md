# DEMO READINESS — Backend prêt pour une démo Expo — `[NOM_PRODUIT]`

> **Version :** 1.0 · **Statut :** AUDIT (backend V1 M1→M12 **gelé**)
> **But :** vérifier qu'une app **Expo** peut fonctionner de bout en bout, et lister
> ce qui reste — **sans ajouter de module backend**.
> **Légende :** 🟢 indispensable démo · 🟡 amélioration facultative · ⚪ production uniquement.

---

## 1. Audit par domaine

| Domaine | État | Classe | Note |
|---|---|---|---|
| **Contrats API mobile** | 8 Edge Functions + RPC, documentés (`API_SPEC` notes V1) | 🟢 | Prêt ; pas de package DTO partagé (doc suffit) |
| **Edge Functions** | health, converse, submit-request, review, estimate-price, zone-check, payments, send-push | 🟢 | `verify_jwt` corrects ; enveloppe `{data}`/`{error}` |
| **RPC** | ~34 (dont mobile : claim_review, transition_mission, payment_intent, mission_overview, operator_queue, admin_stats, get/update_location, mark_*_read, estimate_price, zone_check, validate_config) | 🟢 | `service_role`‑only pour les internes (dispatch, settle, assign, purges) |
| **RLS** | activée sur **toutes** les tables ; vérifiée E2E (M11) | 🟢 | client/opérateur/admin cloisonnés |
| **Policies Storage** | 4 buckets **privés** ; propriétaire (avatars/request-photos/documents), participant (mission-proofs), admin | 🟢 | upload photo = 🟡 pour la démo |
| **Buckets** | avatars, request-photos, mission-proofs, documents (tous privés, MIME+taille) | 🟢 | — |
| **Canaux Realtime** | autorisation `can_access_topic`/`can_publish_topic` + publication (M12) | 🟡 | démo possible en **polling** ; live = confort |
| **Seeds / démo** | catalogue (6 cat.), questions+options, prix défaut, **zone Bruxelles + horaires**, textes i18n, catalogue notifications, toutes les clés config | 🟢 | **manque : comptes de démo** (voir P0) |
| **Variables d'env** | Edge : `SUPABASE_*` (auto) ; `PAYMENT_PROVIDER`/`NOTIFY_TRANSPORT`/`CORS_ALLOW_ORIGIN` **optionnels** (défaut mock/*) | 🟢 | démo tout‑mock = **aucun secret externe** |
| **Secrets** | aucun en dur ; Twilio/Apple/Expo/Stripe = env/Vault, tous **optionnels** en démo mock | 🟢/⚪ | requis seulement pour prod / login réel |
| **Migrations** | 26 fichiers, `db reset` (migrations+seed) OK | 🟢 | — |
| **Indexes** | complets (missions/statut/queue/GIST, notifs/messages non‑lus, thread, audit) | 🟢 | — |
| **Types TypeScript générés** | **absents** (`database.types.ts`) | 🟡 | `supabase gen types` — fortement conseillé, non bloquant |
| **Helpers Supabase** | `_shared/` (auth, cors, http, errors, handler, supabase, env, rpc) | 🟢 | côté Edge ; le mobile utilise `@supabase/supabase-js` |
| **DTO mobile** | décrits dans `API_SPEC` (entrées/sorties par endpoint) | 🟡 | pas de types partagés (générables) |
| **Erreurs par endpoint** | `HttpError`→`{error:{message,code}}` ; RPC→SQLSTATE mappé (`_shared/rpc.ts`) | 🟢 | cohérent |
| **Codes HTTP** | 400/401/403/404/409/422/500 (Edge) ; mêmes via `rpcError` | 🟢 | — |
| **Cohérence JSON** | succès `{ "data": … }`, erreur `{ "error": { message, code } }` | 🟢 | uniforme |
| **États vides** | `operator_queue`→`[]`, `payment`→`null`, listes vides, `next`→`null` en fin d'intake | 🟢 | gérés |
| **Données minimales de test** | catalogue + zone + prix + textes présents ; **coords** fournies par le mobile (géoloc) | 🟢 | Bruxelles : bbox `[4.28,50.78]–[4.48,50.91]` |

---

## 2. Parcours démo réalisable **aujourd'hui** (tout‑mock)

- **Client** (rôle par défaut) : login → `converse` (intake, questions dynamiques) →
  `submit-request` → suit sa mission (`mission_overview`) → paie (`payments` mock) →
  chat (`messages`) → suit la position (`get_operator_location`) → clôture → notifs in‑app.
- **Opérateur** : `operator_queue` → `review` (claim + accept/reject/need_info) → exécution (`transition_mission`) → capture (`payments`).
- **Admin** : `admin_stats`, `validate_config`, édition référentiel (RLS admin).

> ✅ Le **backend supporte le parcours complet en mock**, sans Stripe, sans SMS, sans push réel.

---

## 3. Checklist « Backend prêt pour une démo Expo »

### P0 — Obligatoire avant de développer le front

| # | Élément | Pourquoi | Temps | Bloque la démo ? |
|---|---|---|---|---|
| P0‑1 | **Déployer** migrations + Edge Functions sur un projet Supabase (staging) | L'app Expo a besoin d'une URL + clés réelles | 1–2 h | **Oui** (rien à cibler sinon) |
| P0‑2 | **Amorcer les comptes de démo** : 1 client, 1 **opérateur**, 1 **admin**. Après inscription, promouvoir via SQL (`update profiles set role=…`), car seul un admin peut changer un rôle (garde anti‑escalade) | Sans **opérateur/admin**, impossible de démontrer revue→acceptation→exécution | 30 min | **Oui** (bloque la moitié « opérateur ») |
| P0‑3 | **Vérifier le hook** `custom_access_token` actif → le JWT contient `user_role` | Toute la RLS en dépend | 10 min | **Oui** |
| P0‑4 | **Méthode de login utilisable sur l'appareil** : e‑mail OTP (déjà activé) **ou** Apple/Twilio | `test_otp` téléphone ne marche qu'en local | 0–1 h | **Oui** (login) — e‑mail = 0 dev |
| P0‑5 | **Config démo** : `PAYMENT_PROVIDER=mock`, `NOTIFY_TRANSPORT=mock`, `push_enabled=false` (défauts) | Éviter toute dépendance externe | 5 min | Non (défauts OK) |

### P1 — À faire pendant le développement Expo

| # | Élément | Pourquoi | Temps | Bloque ? |
|---|---|---|---|---|
| P1‑1 | **Générer les types TS** (`supabase gen types typescript`) | Client `supabase-js` typé (DX, moins de bugs) | 15 min | Non |
| P1‑2 | **Abonnements Realtime** (chat `messages`, statut mission, position live) | Confort ; sinon **polling** de `mission_overview`/`get_operator_location` | front | Non |
| P1‑3 | **Upload photos** (request-photos / mission‑proofs) via URLs signées | Preuve de course / photo de demande | front | Non |
| P1‑4 | **Textes i18n manquants** (compléter `content_strings` en/`fr`) au fil des écrans | Aucun texte en dur côté app | itératif | Non |
| P1‑5 | **Login réel** (Apple pour iOS, Twilio SMS) si démo sur device sans e‑mail | Expérience « produit » | 1–2 h | Non (si e‑mail OTP) |
| P1‑6 | **`pg_cron`** actif (expirations/purges) | Démo réaliste des expirations | 10 min | Non |

### P2 — Peut attendre la production

| # | Élément | Pourquoi | Temps |
|---|---|---|---|
| P2‑1 | **Push réel** (Expo + `NOTIFY_TRANSPORT=expo` + webhook secret Vault + `push_enabled=true`) | Notifications hors app | 1 h |
| P2‑2 | **Stripe réel** (`PAYMENT_PROVIDER=stripe`) | Paiements réels | ⚪ |
| P2‑3 | **CORS restreint** (`CORS_ALLOW_ORIGIN`) + CSP (si Expo Web) | Sécurité navigateur | 15 min |
| P2‑4 | **Monitoring / alerting / sauvegardes / rotation clés / rate‑limit** | Exploitation | cf. `DEPLOYMENT.md` |
| P2‑5 | **Auth OTP SMS prod** (Twilio) + SMTP prod | Canal principal en prod | 1–2 h |

---

## 4. Verdict

- **Le backend est FIGÉ et suffisant** pour développer et démontrer une app Expo de
  bout en bout **en mode mock**. Aucune fonctionnalité backend ne manque pour la démo.
- **Seuls 4 points P0** (tous de la **mise en service**, pas du développement) doivent
  être faits **avant** d'attaquer le front : déployer (P0‑1), amorcer les comptes
  client/opérateur/admin (P0‑2), vérifier le claim `user_role` (P0‑3), choisir une
  méthode de login device (P0‑4, e‑mail OTP = zéro dev).
- Tout le reste est **P1 (confort/DX pendant le front)** ou **P2 (production)**.

> **Backend gelé — prêt pour le frontend Expo dès les P0 cochés.**
