# PREMIÈRE MESURE RÉELLE

**Date** 4 septembre 2026 · **Page** `https://pypi.org/project/requests/`
**Empreinte** `ef41f74ee5879fbdb105a1b8eafcf0b646f2267e039941f401eb7329097b6c15`
**Taille** 251 417 octets · **Conservée** `validation/pages_reelles/`

Rejouable :

```
python3 outils/premiere_page_reelle.py \
    --page validation/pages_reelles/2026-09-04-page_web-ef41f74ee587.html \
    --url https://pypi.org/project/requests/ \
    --origine "curl le 2026-09-04" --famille page_web
```

---

## CLASSEMENT DE CETTE MESURE

```
DONNÉE RÉELLE OBSERVÉE        ✓
OPPORTUNITÉ COMMERCIALE       ✗  NON TESTÉE
FAMILLE                       hors plan — aucune des huit
```

Cette page prouve **uniquement** que le système sait rencontrer une vraie page
sans inventer un besoin. **Ce n'est pas une validation commerciale**, et elle
ne doit pas être présentée comme telle. Les deux dimensions restent séparées
partout : voir `validation/PLAN-DE-MESURE.md` et `radar validation`.

## AVERTISSEMENT — CE QUE CETTE MESURE N'EST PAS

**Ce n'est pas la page d'entreprise demandée.** Le réseau sortant de cet
environnement est fermé par la politique de l'environnement : `curl` répond
`CONNECT tunnel failed, response 403`, et `WebFetch` répond `EGRESS_BLOCKED`.
Quatre domaines seulement passent — `pypi.org`, `files.pythonhosted.org`,
`registry.npmjs.org`, `proxy.golang.org` — parce qu'ils servent les
gestionnaires de paquets.

Deux options existaient. Écrire moi-même une page de transporteur belge : ce
serait **un fixture déguisé**, et le compteur « données réelles » deviendrait
un mensonge. Ou mesurer une page que je n'ai pas écrite, sur un domaine
réellement joignable, et **dire exactement ce qu'elle vaut**.

C'est la seconde. Cette page est **réelle** — 251 Ko de HTML que personne ici
n'a rédigés — et elle est **hors sujet commercial**. Elle éprouve donc :

- l'extraction sur du HTML réel et son bruit ;
- la capacité à **ne rien conclure** quand il n'y a rien ;
- la séparation observé / interprété / déduit / inconnu.

Elle **n'éprouve pas** : le score, les capacités, la qualification d'un
besoin, l'action commerciale. `radar validation` l'écrit noir sur blanc :
`PAGES RÉELLES COMPLÈTES : 1 · DONT PORTANT UN BESOIN COMMERCIAL : 0`, et la
prochaine mesure reste **une page réelle qui porte un besoin**.

---

## A · CE QUI ÉTAIT ATTENDU, ÉCRIT AVANT DE MESURER

Le protocole (`--protocole`) fixait cinq échecs possibles :

1. un champ affiché comme lu alors qu'il ne figure pas dans la page ;
2. un état de procédure conclu sur une page qui n'en contient aucune ;
3. un INCONNU traité comme un zéro dans le score ;
4. un rejet causé par l'absence d'un mot attendu ;
5. un score qui dépend d'un champ que ce type de page ne porte jamais.

Et un non-échec explicite : **beaucoup d'INCONNUS**. INCERTAIN vaut mieux
qu'INCORRECT.

---

## B · CE QUI S'EST RÉELLEMENT PASSÉ

| | attendu | observé |
|---|---|---|
| texte lisible | « la majorité de la page » | **5 %** — 12 968 car. sur 251 342 |
| pistes de lecture | toutes ou presque | **6 sur 7** |
| champs extraits | 4 à 6 | **6** |
| état de procédure | HORS PROCÉDURE | **HORS PROCÉDURE** ✔ |
| verdict | rien à en tirer | **🔵 PROSPECT, score 24/100, « SURVEILLER »** ✗ |

Quatre des cinq échecs annoncés ne se sont pas produits. Le cinquième, si —
et deux défauts qui n'étaient sur aucune liste sont apparus.

---

## C · CE QUE LA DONNÉE RÉELLE A RÉVÉLÉ QUE LES FIXTURES NE MONTRAIENT PAS

### 1. Une page sans le moindre fait commercial devenait un prospect à 24/100

Le défaut principal, et il était **invisible en fixture** : les douze familles
d'exemples décrivent douze façons de gagner de l'argent. **Aucune ne décrivait
une page qu'on lit et qui ne donne rien.** Le radar n'avait jamais eu à dire
non à une absence de matière.

Les 24 points venaient entièrement de **neutralités accordées à des absences** :

```
accessibilité PME : +10 — AUCUNE EXIGENCE PUBLIÉE — NON MESURÉ, ni bon ni mauvais
taille adaptée    : +7  — montant NON PUBLIÉ — neutre, jamais pénalisant
géographie        : +6  — aucun lieu publié — zone à vérifier
proximité         : +5  — distance au dépôt NON PUBLIÉE — neutre
marge             : +5  — coûts d'exploitation non renseignés au profil
récurrence        : +4  — cadence NON PUBLIÉE
démarrage         : +4  — moyens nécessaires NON PUBLIÉS
```

Chaque ligne est **juste isolément** : « NON MESURÉ n'est pas zéro » est une
règle verrouillée, et elle protège une vraie affaire dont la source publie
peu. Mais leur **somme** fabriquait une note à partir de rien — et ce 24 se
comparait à un vrai 84 sur la même échelle.

**Corrigé en deux temps.**

- Une sixième catégorie, **⚪ PAS ENCORE UNE OPPORTUNITÉ**. Ni un rejet (rien
  ne dit que cette entreprise n'aura jamais de besoin), ni une file d'attente
  (il n'y a rien à surveiller). Action : `CLASSER SANS SUITE — REVENIR SI UN
  BESOIN APPARAÎT`. Non notifiable.
- Le score devient **NON MESURABLE** quand aucun fait économique n'a été
  observé. `NON MESURABLE ≠ 0`, et surtout `≠ 24`.

Le déclencheur est **l'absence de TOUT fait** — métier, montant, cadence,
durée, échéance, date de démarrage, exigence, besoin exprimé, événement — et
**jamais l'absence d'un mot connu**. Un besoin écrit dans un vocabulaire
inconnu mais daté et chiffré reste une affaire ; c'est verrouillé par
`test_un_besoin_en_vocabulaire_inconnu_reste_une_opportunite`.

### 2. Le JavaScript entrait dans l'analyse sémantique

Le balisage pèse **95 %** du fichier. Le lecteur ramassait le contenu des
`<script>` et `<style>` comme du texte de page : le moteur sémantique
analysait du JavaScript. Une chaîne `"marché attribué le 12/03"` dans un
script publicitaire aurait produit un état de procédure.

Structurellement invisible en fixture : **une fixture est du texte pur.**

### 3. Une absence était présentée comme un argument de vente

```
POURQUOI C'EST INTÉRESSANT POUR MOI
  · aucun lieu publié — zone à vérifier, opportunité conservée
```

La zone `A_VERIFIER` produisait sa raison dans la rubrique des arguments
commerciaux. Le radar vendait un trou. Corrigé : seuls les faits **positifs**
y entrent, et une fiche sans argument le dit — « rien dans cette source ne
constitue un argument commercial ».

### 4. Le contact sortait inutilisable

`mailto:me@kennethreitz.org`. Le préfixe d'un `href` n'est pas une adresse.
Corrigé de façon **déclarative** (`retirer_prefixe`, `couper_a` dans
`sources/page_web.yaml`), pas codé en dur.

### 5. Ajouter une catégorie faisait tomber toute la chaîne

`questions.py` indexait un dictionnaire par `Type`. Ajouter ⚪ a produit un
`KeyError` qui cassait `Moteur.analyser` en entier. Aucun test ne couvrait
« une valeur d'énumération que ce dictionnaire ne connaît pas ».

### 6. Le journal de provenance adressait un reproche faux

Il annonçait : *« mailto:me@… ne figure pas littéralement dans la page
conservée »*. **C'était inexact** : l'adresse figurait bien dans le fichier,
dans un attribut `href`. Le journal ne comparait qu'au **texte visible**.

Les deux existent et ne se valent pas : un lecteur humain ne voit pas la
valeur d'un attribut. D'où un cinquième niveau, **◎ OBSERVÉ DANS LE
BALISAGE**, signalé « invisible pour un lecteur humain de la page ».

---

## D · CE QUI A TENU

- **HORS PROCÉDURE**, sans invention d'état, sur une page qui n'en porte
  aucune. Aucun faux positif.
- **Aucun rejet par absence de mot-clé.**
- Sept INCONNUS, chacun avec **la question à poser** — pas un zéro.
- La preuve de collecte a été contrôlée : la ligne est passée en **mode
  RÉEL**, empreinte vérifiée, livre de comptes réconcilié.
- Le niveau OBSERVÉ a été **refusé deux fois** à des valeurs que le lecteur
  prétendait avoir lues. Le mécanisme contredit bien celui qui l'appelle.

---

## E · RÉPARTITION FINALE

```
◉ OBSERVÉ RÉELLEMENT        4  (19 %)
◎ OBSERVÉ DANS LE BALISAGE  2  ( 9 %)
◐ INTERPRÉTÉ                2  ( 9 %)
◔ DÉDUIT                    6  (28 %)
○ INCONNU                   7  (33 %)
```

**Moins d'un cinquième** de ce que le radar « sait » de cette affaire vient du
texte que l'on peut lire sur la page. Le reste est interprété, calculé, ou
reconnu inconnu — et aucune de ces trois catégories ne doit être présentée à
un client comme un fait lu.

---

## F · TESTS DÉRIVÉS DE CETTE OBSERVATION

Aucun n'est imaginé. Chacun protège un comportement que cette page a pris en
défaut, et se recontrôle sur les octets conservés.

| test | ce qu'il protège |
|---|---|
| `test_le_javascript_nest_pas_du_texte_de_page` | défaut 2 |
| `test_une_page_sans_aucun_fait_commercial_nest_pas_une_opportunite` | défaut 1 |
| `test_ce_nest_pas_un_rejet` | ⚪ ≠ 🔴 |
| `test_un_besoin_en_vocabulaire_inconnu_reste_une_opportunite` | ⚪ ne devient jamais un rejet par mot-clé |
| `test_une_absence_nest_jamais_un_argument_commercial` | défaut 3 |
| `test_ajouter_une_categorie_ne_casse_pas_la_chaine` | défaut 5 |
| `test_le_balisage_est_distingue_du_texte_visible` | défaut 6 |
| `test_le_prefixe_mailto_est_retire` | défaut 4 |
| `test_une_valeur_absente_de_la_page_ne_peut_pas_etre_observee` | le journal doit pouvoir refuser |
| `test_deux_pistes_qui_se_contredisent_sont_signalees` | `<h1>` ≠ `<title>`, observé |
| `test_le_compteur_reel_ne_sinvente_pas_dans_une_phrase` | les deux compteurs |

---

## G · PROCHAINE MESURE

**Une page réelle qui porte un besoin.** Celle-ci a éprouvé l'extraction et le
tri ; elle n'a éprouvé ni le score, ni les capacités, ni l'action.

Il faut, au choix :

- un fichier HTML enregistré depuis un navigateur (page « devenir partenaire
  transporteur », « nos appels à sous-traitance », offre sur une bourse de
  fret) — passé à `--page`, avec `--origine` décrivant exactement sa
  provenance ;
- ou l'ouverture de la politique réseau sur les domaines à observer.

Tant que `DONT PORTANT UN BESOIN COMMERCIAL` reste à 0, la qualification
commerciale du radar n'a **jamais** été confrontée au monde réel.
