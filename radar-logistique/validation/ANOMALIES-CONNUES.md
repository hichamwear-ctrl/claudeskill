# ANOMALIES CONNUES — laissées volontairement intactes

Moteur **gelé** depuis `4e72a04`. Ce fichier est de la documentation : il ne
corrige rien, il empêche d'oublier. Une anomalie connue et écrite vaut mieux
qu'une correction non mesurée.

Rien de ce qui suit ne doit être corrigé tant que la condition de reprise
(egress ouvert, ou HTML bruts déposés avec provenance) n'est pas levée.

---

## A1 — « OPPORTUNITÉS RÉELLES : 3 » compte des mesures, pas des opportunités

**Où** : `radar/validation.py`, ligne d'en-tête du rapport `radar.cli validation`.

**Ce qui se passe** : le compteur additionne les *mesures* dont
`porte_un_besoin` est vrai — recherche du 05/09, marchés publics du 12/09,
recherche du 12/09. Il annonce « opportunités ».

**Pourquoi c'est dangereux** : il affiche `3` au moment où la mesure du 12/09
porte, elle aussi, `3` signaux commerciaux détectés sur titre. Les deux
chiffres coïncident par hasard. Un lecteur pressé y lira trois affaires
gagnées — alors que **0 page a été lue** et que **0 besoin est confirmé**.

**Correction future** : renommer l'intitulé (« MESURES PORTANT UN BESOIN »),
ou compter de vraies opportunités qualifiées. C'est un travail d'intitulé,
pas de logique.

**Statut** : signalé, **non corrigé**. Moteur gelé.

---

## A2 — P1-B : attribution détectée dans du contenu éditorial

**Où** : lecture d'état, `radar/procedure.py`.

**Ce qui se passe** : une phrase éditoriale qui raconte une attribution peut
être lue comme l'état de la procédure.

**Pourquoi ce n'est pas corrigé** : l'étude P1-B.1 a conclu 🔴 NO-GO. La
correction lexicale envisagée a été **mesurée** comme détruisant le cas
« Le marché a été attribué à Transalux SA ». Mieux vaut conserver un faux
positif connu que détruire de vrais marchés attribués.

**Statut** : étudié, mesuré, **délibérément non corrigé**.

---

## A3 — l'intitulé se retrouve dans le corps du document

**Où** : extraction de champs depuis une page HTML réelle.

**Ce qui se passe** : le `<h1>` étant physiquement dans le texte de la page,
l'intitulé apparaît aussi dans `corps`. La prédiction 3 de CORRECTION 1
annonçait le contraire.

**Pourquoi ce n'est pas corrigé** : c'est le comportement d'une vraie page,
pas d'une fixture. Il faut d'autres pages réelles pour savoir si c'est
nuisible. Aujourd'hui il n'y en a qu'une.

**Statut** : mesuré, rapporté, **non corrigé faute de données**.

---

## A4 — même formulation de titre, natures différentes

**Où** : `radar/nature.py`, sur la mesure `recherche` du 12/09.

**Ce qui se passe** : « Sous-traitant DHL : Devenez notre partenaire de
transport » sort 🟢 FAIT, « Devenir prestataire de transport de DHL
Freight » sort ⚪ HYPOTHÈSE. Même promesse, même demandeur, natures
opposées.

**Pourquoi ce n'est pas corrigé** : sur un titre seul, la nature n'est pas
stabilisable — et c'est une raison de plus de ne pas qualifier depuis un
titre. Le juge de cette anomalie sera la page réelle, pas une heuristique
de plus.

**Statut** : mesuré le 12/09, **non corrigé**.

---

## A5 — l'adaptateur `recherche` n'est toujours pas vérifié

**Où** : `sources/recherche.yaml`, `verifie: false`.

**Ce qui se passe** : `recenser` n'a jamais tourné sur une réponse réelle de
moteur ; les champs déclarés n'ont pas été mesurés. Les résultats du 12/09
sont passés par `title` et `url` seulement — les autres clés sont des
suppositions.

**Pourquoi ce n'est pas corrigé** : passer `verifie: true` sans avoir
recensé serait exactement le mensonge que ce drapeau existe pour empêcher.

**Statut** : **honnêtement faux**, à laisser tel quel.

---

## A6 — une expression de prestation ne dit pas qui achète et qui vend

**Où** : `config/roles.yaml`, lexique `prestation.fr`, depuis l'origine.

**Ce qui se passe** : « affrètement », « livraison à domicile »,
« prestataire logistique » décrivent aussi bien le service qu'on ACHÈTE que
celui qu'on VEND. Une vitrine de transporteur qui les emploie ressort donc
`PRESTATAIRE`, et la porte des pages la promeut — non pas parce qu'elle
nomme le métier, mais parce que la règle 3 de `radar/pertinence.py` promeut
sur le RÔLE, et que le rôle se trompe ici de sens.

Exemple mesuré : « Transport routier et affrètement — notre métier depuis
40 ans » → `PRESTATAIRE`, promue.

**Pourquoi ce n'est pas corrigé** : la décision métier 1 a retiré au
VOCABULAIRE son pouvoir de promotion ; elle n'a pas touché au RÔLE, et il
n'a pas été demandé de le faire. Séparer « je cherche ce service » de « je
vends ce service » dans le lexique est une décision métier à part entière,
qui n'a pas été prise.

**Statut** : antérieur aux quatre décisions, **mesuré, non corrigé**, gelé
par `tests/test_decisions_metier.py::D1…test_1bis`.

---

## A7 — un lien externe qui nomme le métier n'est plus retenu comme candidate

**Où** : `radar/liens.py`, `selectionner` — conséquence de la décision 1.

**Ce qui se passe** : un lien vers un AUTRE domaine n'est retenu que s'il
porte un indice `FORTE`. Le vocabulaire métier ayant cessé d'être une preuve
positive, une adresse externe qui ne fait que nommer le métier n'entre plus
du tout — même pas comme candidate.

Mesuré sur la page réelle de Colis Privé : 23 → 22 candidates, et l'adresse
perdue est `https://www.cevalogistics.com/fr`.

**Pourquoi ce n'est pas corrigé** : élargir la rétention de `liens.py` pour
rattraper cette adresse en faisait entrer deux autres — 23 → 25. C'est une
décision métier sur la largeur de la découverte, et elle n'a pas été prise.

**Statut** : **mesuré, non corrigé**, gelé par
`tests/test_deux_circuits.py::S7d…test_2`.
