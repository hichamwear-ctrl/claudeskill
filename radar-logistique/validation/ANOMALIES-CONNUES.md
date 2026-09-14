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
celui qu'on VEND. Une vitrine de transporteur qui les emploie ressort
`PRESTATAIRE`, et la règle 3 de `radar/pertinence.py` promeut sur le RÔLE.

**RÉSOLUE EN PARTIE** — `radar/pertinence.py`, règle 2bis.

La porte lit désormais la contre-preuve qui existait déjà et que la chaîne
utilisait seule : `nature.offre_de_service_dans`. Aucun vocabulaire nouveau,
aucune seconde implémentation — la liste `OFFRE_DE_SERVICE` reste l'unique
dépositaire, et son garde-fou d'origine est conservé : **la demande l'emporte
toujours** sur la vente.

Mesuré sur les 59 entrées du lexique de prestation, trois contextes :

| contexte | avant | après |
|---|---|---|
| vitrine AVEC marqueurs de vente (tarifs, devis, « nos services ») | 45 promues | **1** |
| vitrine NUE, sans aucun marqueur | 45 promues | 45 |
| page qui DEMANDE | 59 promues | **59** — rien perdu |

Sur les cinq adresses jugées du jeu réel du 14/09 : aucun changement.

**CE QUI RESTE** : la vitrine NUE. Rien dans son texte ne dit qu'elle vend,
et le mot seul ne peut pas le dire. Elle reste promue — c'est assumé, pas
oublié : depuis la décision métier 2, une vitrine promue, collectée et
analysée ressort ⚪ CLASSER SANS SUITE. **Elle ne produit plus aucune fausse
opportunité ; elle coûte une place de collecte.**

Corriger ce reste demanderait de trancher « qui achète, qui vend » dans le
lexique lui-même. Mesuré : c'est impossible au niveau du MOT — le même terme
est écrit par les deux parties. La distinction vit dans la phrase, pas dans
le vocabulaire.

**Statut** : **résolue pour la vitrine qui se vend, mesurée et assumée pour
la vitrine nue**. Gelée par
`tests/test_decisions_metier.py::A6_UneVitrineQuiSeVendNEstPasUneDemande`
et `::D1…test_1bis`.

---

## A7 — un lien externe qui nomme le métier n'est plus retenu comme candidate

**Où** : `radar/liens.py`, `selectionner`.

**Ce qui se passait** : un lien vers un AUTRE domaine n'était retenu que s'il
portait un indice `FORTE`. Le vocabulaire ayant cessé d'être une preuve
positive, une adresse externe qui nommait le métier n'entrait plus du tout —
même pas comme candidate. Mesuré sur la page réelle de Colis Privé : 23 → 22
candidates, l'adresse perdue étant `https://www.cevalogistics.com/fr`.

**RÉSOLUE** — un lien externe qui nomme une **FAMILLE** reconnue est de
nouveau retenu comme CANDIDATE, et n'est jamais promu : `promouvable` lit la
confiance, pas cette condition.

Mesuré sur les **quatre** pages réelles archivées :

| règle de rétention | candidates | gagnées | bruit |
|---|---|---|---|
| aujourd'hui (FORTE seul) | 230 | — | — |
| + toute reconnaissance de DOMAINE | 240 | +10 | **8** (dépôt de code, page de login, wiki) |
| + FAMILLE reconnue seulement | 232 | **+2** | **0** |

C'est donc la FAMILLE qui est lue, pas le domaine générique. La distinction
existe déjà : `radar/activite.py` documente le domaine comme l'équivalent
d'un CPV générique, qui confirme qu'on parle de transport sans désigner de
spécialité.

**Statut** : **résolue**. Gelée par
`tests/test_decisions_metier.py::A7_UnLienExterneQuiNommeLeMetierEstRetenu`
et `tests/test_deux_circuits.py::S7d…test_2`.
