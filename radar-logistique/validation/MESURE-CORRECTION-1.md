# CORRECTION 1 — TRANSMISSION DU CONTENU · résultat réel

Prédiction figée en `3003c73`, AVANT le code. Mesure ci-dessous, après.

## Ce qui change matériellement

```
corps    148 → 3 475 car.   (× 23)
texte    210 → 3 475 car.
```

## Différence avant / après — la page Colis Privé

| | après correction 2 | après correction 1 |
|---|---|---|
| Catégorie | ⚪ PAS ENCORE UNE OPPORTUNITÉ | **🟢 DIRECT** |
| Action | CLASSER SANS SUITE | **POSTULER** |
| Familles | `[]` | **`dernier_kilometre`, `logistique_entrepot`** |
| Score | 45 — NON MESURABLE | **55/100 — MESURABLE** |
| État de procédure | HORS PROCÉDURE | **POSTULABLE** |
| Nature | ◇ HYPOTHÈSE | **◆ FAIT** |
| Fiabilité | MOYENNE | **FORTE** |
| Dépôt organisé | non | **oui** |
| Exclusion ADR | écartée (réserve) | **écartée (réserve)** — inchangé |
| Montant · cadence | INCONNU · INCONNU | INCONNU · INCONNU |
| CA | NON PUBLIÉ | NON PUBLIÉ |
| Contradictions | 0 | 0 |

## Vérification des prédictions figées

| | prédiction | résultat |
|---|---|---|
| 1 | `objet` reste la `<meta description>` | ✅ tenue |
| 2 | aucune duplication | ✅ tenue (test dédié) |
| 3 | **l'intitulé n'entre pas dans `corps`** | ❌ **VIOLÉE** — voir ci-dessous |
| 4 | **aucun rejet ADR** | ✅ tenue — la correction 2 n'a pas été défaite |
| 5 | score mesurable par les familles, CA non publié | ✅ tenue |
| 6 | les deux collectes figées ne bougent pas | ✅ `diff` vide sur C et sur D |
| 7 | 500 tests verts sans réécriture | ✅ 509 verts, 0 réécrit |

## Prédiction 3 — violée, et pourquoi

`intitulé dans corps → True`. La règle du §7 — « `corps` = ce que la source dit
EN PLUS de son titre » — ne tient plus, mais **pas** à cause de l'agrégation :
le `<h1>` de la page fait physiquement partie du texte de la page. Le retirer
reviendrait à modifier le contenu, ce que la contrainte interdit.

Aucun double comptage n'a été observé ici : une seule preuve d'état a été
produite, et le mécanisme de fusion du §7 (même rang, même conclusion, même
expression → une preuve, provenances cumulées) reste en place. Mais la
**garantie** structurelle, elle, a disparu : elle reposait sur le fait que le
titre ne pouvait pas être dans le corps.

## Le rapport signal / bruit — mesuré, pas supposé

**Faits nouveaux reçus par le moteur : 4 interprétations là où il y en avait 2.**

Ce qui est JUSTE (3) :

- `dernier_kilometre` et `logistique_entrepot` — exact : la page décrit de la
  livraison de colis, des relais, des lockers, des dépôts ;
- le score devient une mesure parce qu'une famille est reconnue — conforme à
  la règle existante, aucun poids touché ;
- 🟢 DIRECT comme CATÉGORIE est défendable : « Devenir partenaire Colis Privé
  … contribuez à l'expansion du réseau en Belgique et au Luxembourg » est une
  vraie demande de sous-traitance de transport.

Ce qui est FAUX (6) :

- **état POSTULABLE**, sur cette preuve :
  `« corps du document : « disponible » porte sur « offre » » → POSTULABLE`
  Les deux mots viennent de deux phrases sans rapport, à 400 caractères
  l'une de l'autre : « Lockers **Bientôt disponible** » (une feuille de route
  produit) et « Une **offre** de livraison à domicile ou en relais dédiée aux
  e-commerçants » (leur propre argumentaire). **Procédure fantôme.**
- **ACTION POSTULER** : il n'y a aucun dossier à déposer sur cette page.
  C'est l'endroit le plus coûteux où placer du bruit — c'est la ligne que le
  commercial exécute.
- **dépôt organisé = oui**, sur la même matière.
- **nature FAIT** au lieu de HYPOTHÈSE : le besoin n'est pas publié, il est
  déduit d'une page de vitrine.
- **fiabilité FORTE** au lieu de MOYENNE.
- **perte d'un aveu honnête** : « aucune formulation interprétable — état à
  confirmer à la source » a disparu des points à vérifier. Le moteur est passé
  de « je ne sais pas » à « POSTULABLE » sans rien apprendre de vrai.

**Le rapport n'est pas favorable : 3 gains contre 6 dégradations, et le bruit
tombe sur l'ACTION.** C'est exactement le risque annoncé avant l'approbation
— il est maintenant mesuré, pas supposé.

Le radar a bien signalé le danger lui-même, en bas de sa propre sortie :

```
· ⚠ une procédure a été détectée sur une page d'entreprise — à vérifier :
  faux positif possible
```

## Faux positifs

Quatre, tous sur la même page et tous issus du même mécanisme : du texte de
vitrine, de menu et de feuille de route produit lu comme s'il décrivait un
besoin. Aucun ne vient d'une donnée inventée — chaque mot est réellement dans
la page. C'est la PORTÉE du contenu qui manque, exactement comme elle manquait
aux exclusions avant la correction 2.

## Faux négatifs

Aucun introduit. Aucune opportunité présente avant ne disparaît : les deux
collectes figées rendent un `diff` vide, les 12 familles de fixtures aussi.

## Impact sur la notification

**Majeur, et c'est le point à surveiller.** La page passe de « ne pas
notifier » (⚪ CLASSER SANS SUITE) à « notifier avec POSTULER ». Un commercial
recevrait une alerte lui disant de déposer une candidature là où il n'y a
aucun dépôt. L'alerte n'est pas vide — il y a bien un angle commercial, le
partenariat de livraison — mais **l'action annoncée est fausse**.

## Impact sur `POTENTIEL = NON MESURABLE`

L'invariant tient, et il n'a jamais été sollicité dans le sens du blocage :

- après correction 2 : NON MESURABLE, et l'opportunité n'était ni rejetée ni
  masquée — elle était ⚪ faute de fait commercial, pas faute de potentiel ;
- après correction 1 : le score devient mesurable par la reconnaissance du
  métier, pendant que le CA reste NON PUBLIÉ. **Adéquation et potentiel ne
  sont toujours pas fondus.**

Aucun montant, aucune cadence, aucun CA n'a été fabriqué à partir des 3 326
caractères nouvellement lus. La règle absolue sur le CA tient.

## Un point à trancher, pas corrigé ici

`validation/mesures_reelles.json` conserve le verdict ⚪ mesuré le 12 septembre
avant les corrections, dédupliqué par empreinte du fichier. Les mêmes octets
donnent aujourd'hui 🟢. Le registre porte donc un verdict antérieur au moteur
actuel. Je n'y touche pas : ce serait une troisième correction, et le choix
entre « garder l'historique » et « re-mesurer à chaque version du moteur » est
un choix de produit.

## Défaut du HARNAIS trouvé en route (et réparé)

`outils/premiere_page_reelle.py` lisait `preuve.detail`, un attribut qui
n'existe pas sur `Preuve`. La branche n'avait jamais été exécutée : aucune
page réelle n'avait encore produit de procédure détectée. Dès que le corps est
arrivé au moteur, le harnais s'est arrêté sur un `AttributeError`. Remplacé
par `str(preuve)`, qui affiche rang, provenance, observation verbatim et
conclusion. Réparation de l'instrument de mesure, aucune règle touchée.
