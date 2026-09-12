# ATTENTES — FAMILLE D, PORTAIL DE MARCHÉS PUBLICS

**Écrit le 12 septembre 2026, AVANT toute requête.** Horodaté par le commit
qui l'introduit.

## La question mesurée

> **Un titre de listing de marchés publics suffit-il à faire conclure un état
> de procédure que seul le contenu de l'avis peut justifier ?**

C'est la même classe de défaut que « Offres d'emploi » sur la famille C, mais
sur le terrain où elle est la plus probable. Les titres de la famille C ne
contenaient aucun vocabulaire de procédure. Ceux d'un listing de marchés en
contiennent systématiquement : « avis de marché », « attribution »,
« procédure ouverte », « marchés en cours », « clôturé ».

## Ce qui sera collecté, et rien d'autre

Titres et URL **verbatim** rendus par l'outil de recherche. Le résumé en prose
que l'outil produit par-dessus est écrit par un modèle : ce n'est pas une
observation, il n'entre pas. Le réseau sortant reste fermé (`ted.europa.eu`
→ `000`, vérifié le 12/09), donc **aucune page individuelle ne sera lue**.

## Volume attendu

**10 à 20 résultats**, sur 2 à 3 requêtes. Majoritairement des pages d'accueil
de portails et des pages de listing, pas des avis individuels.

## PRÉDICTIONS — ce que le moteur va faire

| # | prédiction | engagement |
|---|---|---|
| P1 | **La majorité des résultats recevront un état ≠ HORS PROCÉDURE** | le vocabulaire de procédure est dans les titres |
| P2 | **Au moins un titre produira POSTULABLE** sans qu'aucun contenu ne le justifie | « marchés en cours », « avis de marché » |
| P3 | **Au moins un titre produira ATTRIBUÉ ou FERMÉ** sans preuve individuelle | « attribution », « résultats », « clôturé » |
| P4 | Aucun CA ne sera mesurable | un titre ne porte pas de montant |
| P5 | Aucun lot ne sera observable | les lots vivent dans l'avis, pas dans le listing |
| P6 | Zéro procédure réellement qualifiable | aucun avis individuel accessible |

## FAUX POSITIFS ANTICIPÉS

1. **POSTULABLE depuis une rubrique.** « Marchés en cours » ou « avis de
   marché » dans un titre de page d'accueil → le moteur conclut qu'on peut
   déposer. **Le plus coûteux** : il envoie préparer un dossier sur une page
   qui n'est qu'un sommaire.
2. **ATTRIBUÉ depuis le mot « attribution ».** Un portail dont la page
   s'appelle « Avis d'attribution » n'a pas un marché attribué : il a une
   rubrique.
3. **FERMÉ depuis une date.** Un titre portant une date passée — « Marchés
   publics 2025 » — produisant une clôture.
4. **Un nom de portail pris pour un acheteur.**

## FAUX NÉGATIFS POTENTIELS

1. Un avis individuel réellement postulable classé ⚪ faute de fait économique
   dans son titre — **conséquence acceptée** de la correction du 5 septembre,
   et à mesurer.
2. Un vrai marché écarté parce que son titre porte un marqueur d'offre.
3. Une opportunité perdue parce qu'un mot du titre a produit un faux FERMÉ.

## HYPOTHÈSE PRINCIPALE

> **Le moteur va sur-interpréter le contexte du listing.** Il traitera le nom
> d'une rubrique comme un état individuel, parce que la hiérarchie des preuves
> accorde le rang 3 au « type d'information » — sans vérifier que ce type
> décrit un AVIS et non une PAGE DE SOMMAIRE.
>
> Autrement dit : la hiérarchie sait qu'une rubrique est plus faible qu'un
> état explicite, mais elle ne sait pas qu'une rubrique **de listing** ne
> décrit aucune procédure individuelle.

## CRITÈRE DE RÉUSSITE / D'ÉCHEC

**RÉUSSITE** — le moteur traite les titres de listing comme ce qu'ils sont :
`HORS PROCÉDURE` ou `INCONNU + question`, jamais POSTULABLE / ATTRIBUÉ /
FERMÉ affirmés depuis un titre seul.

**ÉCHEC** — au moins un titre produit un état affirmé sans preuve individuelle.
**Je prédis l'échec** (P2 et P3).

Si l'échec se produit, la correction ne sera envisagée que si elle explique
une CLASSE de cas, pas un résultat. Si le moteur réussit, **rien ne sera
modifié** — et P1/P2/P3 seront comptées comme fausses.

## Ce que cette campagne ne pourra PAS établir

- qu'un avis individuel est correctement qualifié — aucun n'est accessible ;
- qu'un CA est calculable — un titre n'en porte pas ;
- que les lots sont correctement séparés — ils ne seront pas observables.

Les six cas critiques demandés (listing « en cours » contre avis fermé, lots
d'états différents, contradiction listing/contenu) **ne seront mesurables que
sur une page complète**. Ils seront listés comme non mesurés, pas simulés sur
des fixtures.
