# PLAN DE MESURE — huit familles, aucune principale

> `python3 -m radar.cli validation` affiche l'état réel de ce plan. Ce document
> dit **pourquoi** il est construit ainsi ; la commande dit **où il en est**.

## La règle qui gouverne le plan

Le premier flux réellement disponible ne doit **pas** devenir « la source
principale ». C'est exactement ainsi que TED l'était devenu : non par décision,
mais parce qu'il était le plus facile à brancher. Refaire ça sous un autre nom
serait perdre le travail de plusieurs mois.

Donc : **la prochaine mesure vise toujours une famille non couverte.** C'est
codé, pas promis — `Etat.prochaine_mesure()` refuse de désigner une famille
déjà couverte tant qu'une autre est à zéro, et un test le verrouille.

## Les deux dimensions, qui ne se confondent jamais

| | ce que ça prouve |
|---|---|
| **DONNÉE RÉELLE OBSERVÉE** | le radar a rencontré une donnée qu'il n'a pas fabriquée, et l'a traversée sans casser ni inventer |
| **OPPORTUNITÉ COMMERCIALE TESTÉE** | cette donnée portait un besoin économique, et la qualification a donc été éprouvée |

La seconde ne se déduit **jamais** de la première. La page PyPI mesurée le
4 septembre 2026 est :

```
DONNÉE RÉELLE OBSERVÉE        ✓
OPPORTUNITÉ COMMERCIALE       ✗  NON TESTÉE
```

Elle prouve **uniquement** que le système sait rencontrer une vraie page sans
inventer un besoin. Ce n'est pas une validation commerciale, et elle ne doit
plus jamais être présentée comme telle. Elle est d'ailleurs classée **hors
plan** : elle n'appartient à aucune des huit familles.

## Les huit familles

| | famille | ce qu'elle met à l'épreuve, et que les autres ne mettent pas |
|---|---|---|
| **A** | entreprise privée exprimant un besoin | aucun champ normé, aucune référence, aucun statut, aucun montant. Le besoin est en prose, écrit par celui qui l'a. |
| **B** | bourse de fret | une tournée, une cadence, des points de collecte et de livraison — l'économie est là, la procédure n'existe pas. |
| **C** | moteur de recherche | un titre, un extrait, une URL. Presque rien, et il faut décider si ça vaut d'aller lire la page. |
| **D** | portail de marchés publics | rubriques, statuts, échéances, lots — et les contradictions entre rubrique et fiche. |
| **E** | attribution de marché | un marché déjà pris. Le titulaire devra exécuter : c'est une piste, pas un déchet. |
| **F** | signal économique | un événement, pas une demande. Ouverture de dépôt, recrutement massif, implantation. |
| **G** | renouvellement de contrat | un contrat existant dont l'échéance approche. Le besoin est certain, la fenêtre est datée. |
| **H** | partenariat / sous-traitance | quelqu'un cherche un partenaire, pas un fournisseur. La relation est l'objet. |

Chacune alimente **le même pipeline**, sans exception :

```
SOURCE → COLLECTE → PREUVE → EXTRACTION → NORMALISATION → NATURE
       → ÉTAT DE PROCÉDURE (si applicable) → CAPACITÉ → ÉCONOMIE
       → SCORE → ACTION → FIL DE VIE
```

Et aucune étape métier n'a le droit de demander « est-ce TED ? ». C'est
vérifié mécaniquement : un test analyse l'AST des modules du cœur et échoue si
un nom de portail apparaît dans du **code exécutable** (les commentaires
peuvent citer TED en exemple, le code non).

## Ce que chaque mesure doit produire

1. la page ou la réponse brute, **conservée**, avec son SHA-256 ;
2. l'origine exacte — comment la donnée a été obtenue, pas « collectée » ;
3. les quatre niveaux de provenance, dont **OBSERVÉ vérifié** contre les octets ;
4. le passage complet dans la chaîne, en mode RÉEL ;
5. le verdict, et s'il portait ou non un besoin ;
6. ce que la donnée réelle a révélé que les fixtures ne montraient pas.

## Ce qui bloque aujourd'hui

Le réseau sortant est fermé par la politique de l'environnement. Quatre
domaines passent (`pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org`,
`proxy.golang.org`) parce qu'ils servent les gestionnaires de paquets — aucun
ne porte de besoin de transport.

Deux voies pour avancer, au choix :

- **fournir un fichier** enregistré depuis un navigateur, pour n'importe
  laquelle des huit familles :
  ```
  python3 outils/premiere_page_reelle.py --page fichier.html \
      --url https://... --origine "enregistrée depuis Firefox le 5/9" \
      --famille bourse_fret --completude "page complète"
  ```
- **ouvrir la politique réseau** sur les domaines à observer.

Tant que `OPPORTUNITÉ COMMERCIALE TESTÉE` reste à 0, la qualification
commerciale du radar n'a jamais été confrontée au monde réel — quel que soit
le nombre de tests.
