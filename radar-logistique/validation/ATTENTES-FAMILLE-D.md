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

---

# RÉSULTATS — 12 septembre 2026

15 résultats réels, 2 requêtes, brut conservé et haché
(`bb3b99a2bab543df…`). Aucune page individuelle lue : `ted.europa.eu`,
`online.govex.be` → `000`.

## PRÉDIT | OBSERVÉ | ÉCART | EXPLICATION

| # | PRÉDIT | OBSERVÉ | ÉCART | EXPLICATION |
|---|---|---|---|---|
| — | 10 à 20 résultats | **15** | aucun | — |
| P1 | la majorité ≠ HORS PROCÉDURE | **9/15** (8 INCONNU + 1 ATTRIBUÉ) | **juste, de peu** | 6 titres ne portaient aucun marqueur |
| P2 | au moins un **POSTULABLE** sans preuve | **0** | **FAUX sur le réel** | aucun titre collecté ne disait « en cours » près de « offres » ; le moteur **le fait** sur variante — défaut latent, pas déclenché |
| P3 | au moins un **ATTRIBUÉ/FERMÉ** sans preuve | **1 ATTRIBUÉ** | **juste** | « Avis d'attribution de march \| » → ATTRIBUÉ, rang 4 |
| P4 | aucun CA mesurable | **0** | aucun | un titre ne porte pas de montant |
| P5 | aucun lot observable | **0** | aucun | les lots vivent dans l'avis |
| P6 | zéro procédure qualifiable | **1** | **FAUX** | l'ATTRIBUÉ de P3 est compté qualifiable (confiance moyenne) — c'est le défaut, pas une capacité |

**Mon hypothèse principale était juste** : le moteur sur-interprète le contexte
du listing. Mais **moins souvent que prédit sur le réel** (1 cas sur 15), et
**plus gravement que prédit sur la classe** (5 sur 8 en reproduction).

## MESURES SÉPARÉES

```
pages réellement observées          : 0     (réseau fermé)
procédures réellement qualifiables  : 1     ← et c'est le défaut
états INCONNU                       : 8
états HORS PROCÉDURE                : 6
états AFFIRMÉS depuis un titre seul : 1
lots observables                    : 0
CA réellement mesurable             : 0 €
```

## 1. CE QUI EST DÉMONTRÉ SUR DONNÉES RÉELLES

- **Aucun CA n'est inventé depuis un titre.** 15/15 en `NON PUBLIÉ →
  IMPOSSIBLE À MESURER`.
- **Aucun lot fantôme.**
- **8 titres opaques sur 15 → INCONNU + VÉRIFIER**, sans invention. Les avis
  BDA numérotés (`N. 438555`, `N. 648055`…) ne portent aucun texte : le
  moteur ne conclut rien.
- **Un état affirmé depuis un titre seul**, reproductible.

## 2. CE QUI RESTE SUPPOSÉ

Tout ce qui vit dans l'avis : besoin, demandeur, volume, cadence, véhicules,
durée, exigences, montant, échéance, lots, et l'état réel de la procédure.
**Zéro page lue.**

## 3. FAUX POSITIFS — reproduits sur variantes

| titre | état affirmé | preuve invoquée |
|---|---|---|
| « Avis d'attribution — Les marchés publics en Wallonie » | **ATTRIBUÉ** | rang 4, « attribution » |
| « Rubrique : avis d'attribution » | **ATTRIBUÉ** | rang 4, « attribution » |
| « Appels d'offres en cours — portail » | **POSTULABLE** | rang 2, « en cours » sur « offres » |
| « Résultats des marchés publics 2025 » | **FERMÉ** | rang 2, « resultats » |
| « Avis de préinformation — liste » | **ANNONCÉ** | rang 4, « preinformation » |

**5 sur 8.** Ce n'est pas un cas isolé, c'est une classe.

Deux titres ont échappé — « Marchés en cours | Bulletin des adjudications » et
« Marchés clôturés | archives » → HORS PROCÉDURE. L'incohérence tient au
voisinage des mots, pas à une règle : le moteur n'a **aucune** notion de
« ce texte nomme une rubrique ».

## 4. FAUX NÉGATIFS POTENTIELS

- Un avis réellement postulable classé ⚪ faute de fait économique dans son
  titre. **Observé 6 fois sur 15** — conséquence assumée de la correction du
  5 septembre, mais c'est bien un faux négatif pour la découverte.
- Aucun faux FERMÉ observé cette fois (le correctif « plus de » tient).

## 5. ERREURS DE DONNÉES / INFORMATIONS INSUFFISANTES

- « Avis d'attribution de march **|** » — titre réellement tronqué à la source.
- « 1 Version 01 janvier 2026 » — un PDF dont le titre est un fragment.
- Les titres BDA n'exposent qu'un numéro et un UUID : **aucune information
  exploitable**, et c'est la règle sur ce portail, pas l'exception.

## 6. IMPACT COMMERCIAL

**Le faux ATTRIBUÉ est le plus coûteux.** Un avis encore postulable rangé en
ATTRIBUÉ sort de « À ATTAQUER » et passe en « CONTACTER LE TITULAIRE ». On ne
dépose pas. **Le marché est perdu sans qu'aucune ligne ne le signale.**

Le faux POSTULABLE coûte moins : on prépare un dossier pour rien.

Sur un listing réel de plusieurs centaines de titres, la proportion observée
en reproduction (5/8) rend le tri inexploitable sans lecture des avis.

## 7. MODIFICATION À ENVISAGER — non appliquée

### La cause racine, trouvée en cherchant le correctif

```python
# radar/adaptateur.py
texte = " ".join(str(c.get(k, "")) for k in ("objet", "intitule", "lieu", "conditions"))
```

**L'adaptateur recopie l'intitulé dans le texte.** Chaque preuve tirée du
titre est donc comptée **deux fois** — « intitulé : attribution » ET
« description : attribution » — et le moteur ne peut structurellement pas
distinguer « le titre le dit » de « le corps le dit ».

Conséquences mesurées :
1. tout enregistrement réduit à un titre paraît **corroboré** ;
2. la hiérarchie des preuves est en partie **fictive** : « description » n'est
   pas une source distincte quand elle contient le titre ;
3. deux preuves de rang 4 concordantes donnent une confiance imméritée.

### La règle générale proposée

> **Un intitulé NOMME un type de document ; il n'énonce pas l'état d'une
> procédure.** Sans corroboration — description propre, statut déclaré,
> événement, titulaire, date d'attribution — le titre *propose* et ne
> *tranche* pas : l'état devient INCONNU avec la question à poser.

Le module applique **déjà ce principe aux documents joints** : « le statut
d'un document n'est pas celui de la procédure ». Il ne l'applique pas au titre
de l'enregistrement lui-même.

### Impact mesuré du correctif, en copie de travail

- 4 modules touchés : `adaptateur.py`, `modele.py`, `chaine.py`, `procedure.py` ;
- **19 tests sur 467 cassent** — tous parce qu'ils construisent
  `Opportunite(texte=…)` directement, sans passer par l'adaptateur ;
- séparer proprement le titre du corps demande un champ de modèle nouveau et
  une revue du banc d'essai.

**Ce n'est pas un correctif d'une ligne.** Je ne l'ai pas appliqué : la
décision revient au propriétaire du produit.
