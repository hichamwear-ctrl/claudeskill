# Photos produits

Déposez ici vos **vraies photos** (celles envoyées dans le chat), avec **exactement ces noms** —
elles s'afficheront automatiquement sur la boutique et les fiches produit :

| Produit                                   | Nom de fichier attendu            |
|-------------------------------------------|-----------------------------------|
| Miel de Litchi (Madagascar)               | `litchi.jpg`                      |
| Miel de Jujubier (Algérie)                | `jujubier.jpg`                    |
| Miel & Curcuma                            | `curcuma.jpg`                     |
| Miel, Gelée Royale, Pollen & Propolis     | `gelee-royale.jpg`                |
| Miel, Citron Vert & Gingembre             | `citron-gingembre.jpg`            |

Photos d'ambiance optionnelles (page d'accueil et « À propos ») :

| Emplacement            | Nom de fichier attendu |
|------------------------|------------------------|
| Grande image du hero   | `../hero.jpg`          |
| Photo « La maison »    | `../about.jpg`         |

## Notes
- Format conseillé : **JPG ou WebP**, carré (1:1) pour les produits, ~1000×1000 px.
- Tant qu'un fichier est absent, un **dégradé miel élégant avec le nom du produit** s'affiche
  à la place (aucune image cassée).
- Les prix du catalogue sont des **valeurs par défaut** : ajustez-les dans
  `assets/app.js` (tableau `CATALOG`, champs `price` / `old`).
