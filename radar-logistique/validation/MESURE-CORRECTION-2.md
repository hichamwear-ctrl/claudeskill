# CORRECTION 2 — PORTÉE DES EXCLUSIONS · résultat réel

Prédiction figée en `f5b3e15`, AVANT le code. Mesure ci-dessous, après.

## Différence avant / après — la page Colis Privé

Sortie complète de `outils/premiere_page_reelle.py`, avant contre après :

```
143a144,146
> OBSERVÉ MAIS ÉCARTÉ — À VÉRIFIER
>   ⚠ activité exclue « adr » observée en [pied de page] — écartée : ne
>     caractérise pas le besoin. Extrait : « …vé FAQ – partenaire de livraison
>     À propos CGU Mentions légales Normes ADR © 2026 Colis Privé par CEVA
>     Logistics »
226c229
<   TESTS DE COHÉRENCE : 483
---
>   TESTS DE COHÉRENCE : 500
```

**Trois lignes ajoutées. Rien d'autre n'a bougé.**

| | avant | après |
|---|---|---|
| Catégorie | ⚪ PAS ENCORE UNE OPPORTUNITÉ | ⚪ PAS ENCORE UNE OPPORTUNITÉ |
| Action | CLASSER SANS SUITE | CLASSER SANS SUITE |
| Motif | aucun fait commercial observé | aucun fait commercial observé |
| Familles | `[]` | `[]` |
| Score | 45 — NON MESURABLE | 45 — NON MESURABLE |
| Exclusions bloquantes | `[]` | `[]` |
| Réserve ADR | absente | **affichée, avec origine et extrait** |

Conforme à la prédiction, y compris sur le point où elle contredisait le
résultat espéré : **ce n'est pas 🟢 DIRECT**, et ce ne devait pas l'être.
Les 148 caractères disponibles ne contiennent aucun fait commercial. Le 🟢
attendu dépend de la CORRECTION 1, pas de celle-ci.

## Segmentation réellement obtenue

```
[corps de la page      ]    88 car.
[navigation            ]   298 car.
[corps de la page      ]  2703 car.
[pied de page          ]   234 car.   ← « Normes ADR » est ici, et nulle part ailleurs
[description de la page]   148 car.
```

## Les deux collectes déjà figées

```
diff mesure_famille_c  avant/après  →  IDENTIQUE
diff mesure_famille_d  avant/après  →  IDENTIQUE
```

Aucune source de ces collectes ne déclare de segments : elles empruntent le
chemin d'avant, à l'octet près.

## Faits nouveaux reçus par le moteur

**Aucun fait nouveau pour la qualification.** C'est délibéré : `segments` est
une vue PORTÉE du même matériau, lue par le seul chemin des exclusions. Les
familles et le domaine continuent de lire exactement `texte`.

Le seul élément nouveau est une PROVENANCE : « adr » a été lu en pied de page.

## Nouvelles contradictions

Aucune. Le mécanisme de contradiction vit dans `procedure.py`, que cette
correction ne touche pas.

## Faux positifs

Aucun observé. Le risque annoncé — une exclusion réelle logée dans une zone
classée non caractérisante — est verrouillé par quatre tests :

- une **rubrique** (« Marchés › Transport de matières dangereuses ») bloque :
  une rubrique nomme la catégorie du marché, elle n'est pas un menu ;
- une **origine non déclarée** bloque : l'inconnu caractérise ;
- une exclusion **bloquante et une écartée ensemble** → la bloquante gagne ;
- un `<div class="site-footer">` est reconnu comme pied de page : un verdict
  commercial ne doit pas dépendre de la qualité du HTML.

## Faux négatifs

Un faux négatif corrigé **en puissance, pas encore en acte** : sur le dépôt
d'aujourd'hui la page n'était pas rejetée pour ADR — le mot n'atteignait pas
le moteur. La correction rend le rejet impossible AVANT que la CORRECTION 1
n'amène le pied de page jusqu'au moteur. C'est l'ordre demandé, et c'est le
bon : appliquée dans l'autre sens, la correction 1 aurait créé le rejet.

Aucun faux négatif introduit : la vue portée ne remplace la chaîne aplatie que
pour les sources qui déclarent des segments, et ces segments couvrent alors
tout le texte de la page, l'intitulé et la description `<meta>` comprises.

## Impact sur la notification

Nul. Le classement, l'action et le moteur sont inchangés — donc la décision de
notifier l'est aussi. Une exclusion écartée n'ajoute qu'une ligne à la fiche.

## Impact sur `POTENTIEL = NON MESURABLE`

Nul, et vérifié par un test dédié : sans fait économique ni famille reconnue,
le score reste NON MESURABLE — et cela ne produit ni rejet, ni masquage, ni
absence d'alerte. L'invariant tient.

## Ce que cette correction ne prouve pas

Qu'une opportunité commerciale a été trouvée. Il n'y en a toujours aucune sur
cette page tant que la matière n'y arrive pas.

## Défaut du BANC D'ESSAI trouvé en route (et réparé)

`tests/test_radar.py` portait un `if __name__ == "__main__": unittest.main()`
**au milieu du fichier**, ligne 546. `python tests/test_radar.py` n'exécutait
donc que **70 méthodes sur 500** — les 430 suivantes n'étaient jamais jouées
par cette commande. Le garde a été déplacé à la fin du fichier. C'est une
réparation de l'INSTRUMENT DE MESURE, pas une troisième correction : aucune
assertion n'a été touchée.

Les 483 méthodes d'origine sont intactes — la seule suppression dans le
fichier de tests est ce garde mal placé. 483 + 17 nouvelles = 500, toutes
vertes.
