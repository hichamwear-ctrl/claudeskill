# ATTENTES — AVANT DE REGARDER LA DONNÉE

**Écrit le 5 septembre 2026, AVANT toute recherche.** Horodaté par le commit
qui l'introduit. Le but est de pouvoir dire ensuite « le modèle s'est trompé »
plutôt que « j'ai ajusté le modèle ».

## Ce qui va être mesuré

La famille **C — moteur de recherche**. Le réseau sortant reste fermé sur tous
les domaines (`curl` → `000` sur ted.europa.eu, bpost.be, publicprocurement.be,
teamtransport.be), mais l'outil de recherche répond et rend des **URL et des
titres réels**, non fabriqués ici.

Ce qui sera utilisé, et rien d'autre : **le titre verbatim et l'URL verbatim**
tels que l'outil les rend. Le résumé en prose que l'outil produit par-dessus
est écrit par un modèle — il ne sera PAS ingéré. Un résumé n'est pas une
observation.

## Ce que le radar DEVRAIT faire, si le modèle est juste

Un résultat de recherche ne porte qu'un titre et une URL. Donc :

| dimension | attendu | pourquoi |
|---|---|---|
| CA | `NON PUBLIÉ → IMPOSSIBLE À MESURER` | un titre ne porte pas de montant |
| état de procédure | `HORS PROCÉDURE` | un titre ne porte aucun marqueur de procédure |
| capacité | `NON MESURÉE — aucune exigence publiée` | rien à confronter |
| score | `NON MESURABLE` sur la plupart | aucun fait économique observé |
| catégorie | ⚪ **PAS ENCORE UNE OPPORTUNITÉ** sur la plupart | conséquence du précédent |

## LA PRÉDICTION QUI ENGAGE

> **La plupart des résultats ressortiront ⚪ PAS ENCORE UNE OPPORTUNITÉ, et
> aucun ne deviendra une opportunité commerciale qualifiée.**
>
> Raison : un titre de trois mots ne porte aucun fait économique. Le
> déclencheur de ⚪ est l'absence de TOUT fait — pas l'absence d'un mot-clé —
> et un titre n'en porte aucun.
>
> **Conséquence si la prédiction se vérifie : la famille C ne peut pas, seule,
> produire une opportunité qualifiée. Elle sert à TROUVER des pages, pas à les
> qualifier.** Ce serait un enseignement sur l'architecture, pas un défaut.

## Ce qui compterait comme une SURPRISE

- un résultat qui ressort qualifié alors qu'il ne porte qu'un titre ;
- un état de procédure conclu depuis un titre ;
- un montant apparu de nulle part ;
- un rejet causé par l'absence d'un mot attendu ;
- un titre porteur d'un vrai besoin classé ⚪ à tort.

## La règle que je m'impose

**Aucune modification du moteur pour faire passer ce cas.** Si l'écart est
réel, il est décrit et laissé ouvert. Le corriger dans la foulée reviendrait à
ajuster le modèle sur son propre examen.
