# Miels du Monde — site premium (HTML/CSS/JS, sans build)

Site multi-pages autonome : ouvrez simplement `index.html` dans un navigateur.
Aucune installation, aucune dépendance à builder. Polices via Google Fonts.

## Pages
| Fichier         | Rôle                                             |
|-----------------|--------------------------------------------------|
| `index.html`    | Accueil (hero, piliers, sélection, labo, avis)   |
| `boutique.html` | Boutique + filtres (miels d'origine / préparations) |
| `produit.html`  | Fiche produit (`produit.html?p=<slug>`)          |
| `a-propos.html` | Qui sommes-nous                                  |
| `faq.html`      | FAQ                                              |
| `checkout.html` | Paiement sécurisé (CB, PayPal, Bancontact, Apple/Google Pay) |
| `admin.html`    | **Panel admin** (tableau de bord, commandes, clients, produits) |

Assets partagés dans `assets/` : `style.css`, `app.js`, `admin.css`, `admin.js`,
le logo (`logo.png` / `logo-light.png` + fallback SVG) et les photos dans `assets/products/`.

## Logo & photos
Le **vrai logo** et les **7 vraies photos produits** sont intégrés
(`assets/logo.png`, `assets/products/*.webp|png`). Pour remplacer une image,
écrasez simplement le fichier du même nom.

## Panier & commandes (« connecté en direct »)
- Le panier persiste entre les pages via `localStorage` (`mdm_cart_v1`).
- À chaque paiement validé, la commande est enregistrée dans `localStorage`
  (`mdm_orders`) avec client, articles, totaux, paiement, livraison, statut.
- Le **panel admin** (`admin.html`) lit ces commandes **en temps réel** (même
  navigateur) : KPIs, graphique de revenus, top produits, table de commandes,
  clients agrégés, analytics produits, et **recherche** par nom / n° de commande
  / e-mail. Statuts modifiables. Bouton pour générer des commandes de démo.
- Accès démo : n'importe quel mot de passe sur l'écran de connexion.

### Passer à un vrai backend (multi-appareils, persistant)
L'admin est volontairement branché sur `localStorage` pour fonctionner en HTML
pur. Pour un backend serveur (multi-appareils, sécurisé) :
1. Remplacez `load()` / `save()` dans `assets/admin.js` et l'enregistrement de
   commande dans `assets/app.js` (`recordOrder`) par des appels à une API
   (Supabase, Firebase, ou votre propre serveur).
2. Branchez un vrai PSP sur le paiement (Stripe / PayPal / Mollie pour
   Bancontact) — le front est prêt (méthodes déjà présentes).
3. Ajoutez une authentification réelle sur `admin.html`.

## Détails premium
- Transitions « miel » entre les pages (voile doré) + reveals au scroll.
- Panier tiroir avec accent doré / nid d'abeille, barre de livraison offerte,
  animation « fly-to-cart ».
- Design system : Cormorant Garamond + Inter · palette noir/crème/or/ambre/miel.
- Accessible (focus visibles), responsive, `prefers-reduced-motion` respecté.
