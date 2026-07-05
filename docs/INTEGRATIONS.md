# Intégrations — brancher les fournisseurs réels

Toutes les intégrations externes fonctionnent en **mode mock par défaut** (aucune
clé requise) et se remplacent par un fournisseur réel via une interface propre.
Le projet est prêt à recevoir les clés de production : renseignez les variables
`.env` et implémentez/activez l'adaptateur — **aucun composant ni route à modifier**.

## Vue d'ensemble

| Domaine | Interface | Défaut (mock) | Adaptateur réel | Où brancher |
|---|---|---|---|---|
| Temps réel | `RealtimeTransport` (`src/lib/realtime.ts`) | `InMemoryTransport` | Supabase Broadcast | `src/server/realtime/supabase.ts` |
| Paiement | `PaymentProvider` (`src/server/payments/provider.ts`) | `mockPaymentProvider` | Stripe | `src/server/payments/stripe.ts` |
| Email | `EmailProvider` (`src/server/notifications/email.ts`) | `consoleEmailProvider` | Resend/SendGrid/SES | `setEmailProvider(...)` |
| SMS | `SmsProvider` (`src/server/notifications/sms.ts`) | `consoleSmsProvider` | Twilio/Vonage | `setSmsProvider(...)` |
| ETA / routing | `RoutingProvider` (`src/lib/routing.ts`) | `haversineRoutingProvider` | Google Directions/Mapbox | `setRoutingProvider(...)` |
| Carte | `TrackingMapProps` / `MapProvider` (`src/components/map/types.ts`) | `SvgTrackingMap` | Leaflet / Google Maps | nouveau composant + `NEXT_PUBLIC_MAPS_PROVIDER` |

---

## 1. Temps réel — Supabase Realtime

**Env :** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`, `REALTIME_CHANNEL_SECRET`.

- Sans env → `getServerTransport()` renvoie `InMemoryTransport` et le
  `RealtimeProvider` reste inerte (`status: "disabled"`). L'app fonctionne à
  l'identique (données revalidées à l'événement quand configuré).
- Avec env → broadcast par réservation (`reservation:{id}`). Les tokens de canal
  sont signés côté serveur (`src/server/realtime/auth.ts`).
- **Durcissement conseillé :** activer la **Realtime Authorization (RLS)** Supabase
  pour refuser les abonnements non autorisés côté serveur (en plus du token app).

## 2. Paiement — Stripe

**Env :** `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`,
`STRIPE_WEBHOOK_SECRET`.

- Sans clé → `mockPaymentProvider` règle le paiement **en ligne** (statut `paid`)
  et émet la facture, sans transaction réelle.
- Avec `STRIPE_SECRET_KEY` → `createStripeProvider` crée une **Checkout Session**
  hébergée ; le client est redirigé, et `/api/payments/webhook` confirme sur
  `checkout.session.completed`.
- **Webhook :** configurer l'endpoint Stripe sur `POST /api/payments/webhook`.

## 3. Email

**Défaut :** `consoleEmailProvider` (log). **Brancher :** implémenter
`EmailProvider.send()` (ex. Resend) puis appeler `setEmailProvider(myProvider)`
dans un fichier de bootstrap serveur. Les templates sont dans
`src/server/notifications/templates.ts` (une seule source pour tous les canaux).

## 4. SMS

**Défaut :** `consoleSmsProvider`. **Brancher :** implémenter `SmsProvider.send()`
(ex. Twilio) et `setSmsProvider(...)`. Même dispatcher que l'email/temps réel
(`src/server/notifications/index.ts`) — aucun code dupliqué.

## 5. ETA / routing

**Défaut :** `haversineRoutingProvider` (distance à vol d'oiseau + vitesse ville).
**Brancher :** implémenter `RoutingProvider.calculateEta()` (Google Directions,
trafic temps réel) et `setRoutingProvider(...)`. Le publisher temps réel
(`src/server/realtime/publisher.ts`) et l'UI restent inchangés.

## 6. Carte

**Défaut :** `SvgTrackingMap` (autonome, sans tuiles, sans clé). **Brancher :**
créer un composant Leaflet/Google respectant `TrackingMapProps`
(`{ client, barber }`) et le sélectionner selon `NEXT_PUBLIC_MAPS_PROVIDER`
(+ `NEXT_PUBLIC_GOOGLE_MAPS_KEY`). Les positions arrivent déjà via le canal
temps réel — aucun changement de flux.

---

### Récapitulatif des variables d'environnement

Voir `.env.example`. Tant qu'une variable reste vide, l'intégration correspondante
utilise son fournisseur mock. Renseigner la variable **suffit** à activer le réel
(après implémentation de l'adaptateur listé ci-dessus).
