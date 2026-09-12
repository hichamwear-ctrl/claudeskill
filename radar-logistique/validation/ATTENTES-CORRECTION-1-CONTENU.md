# CORRECTION 1 — TRANSMISSION DU CONTENU · prédiction figée AVANT le code

Figée le 2026-09-12, après la mesure de la correction 2 (`9e87a84`), avant
toute modification de l'adaptateur.

## Ce qui change matériellement

```
avant :  opp.corps = 148 car.   (la description <meta>)
après  :  opp.corps ≈ 3 300 car. (la description <meta> + le texte de la page)
          soit 22 × plus de matière, dont on ne sait pas encore la part utile
```

## Ce que je NE sais pas prédire, et que je refuse de deviner

Le rapport signal/bruit. C'est précisément ce qu'il faut mesurer. Je fige donc
ce que j'attends du MÉCANISME, pas le verdict.

## Prédictions vérifiables

1. **`objet` reste la description `<meta>`**, inchangée. `contenu` est un champ
   distinct. Aucun des deux n'écrase l'autre.
2. **Aucune duplication** : la description `<meta>` n'apparaît qu'une fois dans
   `corps`, même si une source la publiait aussi comme corps.
3. **L'intitulé n'entre pas dans `corps`** — la règle du §7 tient sur 3 300
   caractères comme sur 148.
4. **Pas de rejet ADR.** Le mot arrive maintenant dans `corps`, mais le chemin
   des exclusions lit les segments, pas `corps`. Si un 🔴 REJET ADR apparaît,
   **la correction 2 a été défaite par la correction 1** — c'est le défaut le
   plus grave possible ici, et il est testable.
5. **Le score devient probablement MESURABLE**, par les familles reconnues et
   non par un fait économique. Ce serait un progrès de reconnaissance, pas un
   progrès économique : le CA doit rester NON PUBLIÉ. Si un montant apparaît,
   il faut vérifier d'où il sort avant de s'en réjouir.
6. **Les deux collectes figées ne bougent pas** : ni `recherche.yaml` ni
   `portail.yaml` ne déclarent de champ `contenu`.
7. **Les 500 tests restent verts, sans réécriture.**

## Les deux issues possibles sur la page, et ce qu'elles signifient

| issue | lecture |
|---|---|
| 🟢 ou 🟡 avec des familles reconnues | la matière portait bien un ancrage commercial |
| ⚪ maintenu parce que la page est une OFFRE | correct : Colis Privé vend du transport, il n'en achète pas — sauf pour ses « partenaires de livraison » |

**Aucune des deux n'est un échec.** Un ⚪ maintenu sur une page de vitrine est
un bon résultat ; un 🟢 arraché à une page qui n'exprime aucun besoin serait un
faux positif. Je ne toucherai ni `est_une_offre`, ni l'ancrage, ni un poids
pour faire sortir 🟢.

## Le bruit à compter, sans le corriger

À relever et à rapporter, pas à réparer dans ce commit :

- familles reconnues par du texte de menu ou de vitrine ;
- procédures fantômes créées par des formulations de navigation ;
- contradictions nouvelles dans la lecture d'état ;
- montants ou cadences captés dans des blocs sans rapport avec un besoin.

Si le bruit l'emporte, la conclusion sera « la transmission du contenu exige
une notion de portée pour le contenu aussi » — et ce sera un chantier suivant,
à décider, pas à lancer.
