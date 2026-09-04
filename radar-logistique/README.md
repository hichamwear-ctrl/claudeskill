# RADAR COMMERCIAL MULTI-SOURCES — transport et logistique

Le radar détecte des opportunités de chiffre d'affaires provenant de
**différentes familles de sources prévues par l'architecture**, les qualifie
économiquement, distingue les **faits** des **signaux** et des **hypothèses**,
puis indique comment les **attaquer**, les **développer**, les **surveiller**
ou les **convertir**.

> Ce n'est pas « de n'importe quelle source ». Une famille **prévue** par
> l'architecture n'est pas une famille **validée sur le monde réel**.

L'état exact se lit avec `python3 -m radar.cli validation`, qui ne mélange
jamais ce qui ne se déduit pas l'un de l'autre :

| compteur | ce qu'il prouve |
|---|---|
| **TESTS DE COHÉRENCE** | des régressions ne passeront plus, sur des données **fabriquées**. Aucune capacité réelle. |
| **DONNÉE RÉELLE OBSERVÉE** | le radar a traversé une donnée qu'il n'a pas fabriquée, sans casser ni inventer. |
| **OPPORTUNITÉ COMMERCIALE TESTÉE** | cette donnée portait un **besoin économique** — le seul compteur qui parle de valeur commerciale. |

Le plan de mesure couvre **huit familles**, et aucune n'est la principale : le
premier flux disponible ne doit pas le devenir par accident. Voir
`validation/PLAN-DE-MESURE.md`.

Ce n'est pas un moteur d'appels d'offres. Ce n'est pas un radar TED. L'appel
d'offres est **une catégorie d'opportunités parmi d'autres** ; TED est **un
capteur parmi d'autres**.

> **LE CENTRE DU RADAR N'EST PAS LA SOURCE.**
> **LE CENTRE DU RADAR N'EST PAS L'APPEL D'OFFRES.**
> **LE CENTRE DU RADAR EST LE BESOIN COMMERCIAL ET SA RENTABILITÉ.**

La question posée à chaque étage :

> Est-ce que cette entreprise peut réellement obtenir ce contrat avec ses
> capacités actuelles, éventuellement en louant du matériel, en recrutant ou
> en travaillant avec un partenaire ?

Et jamais : « est-ce que cette annonce contient le mot transport ? », ni
« est-ce que ça vient d'une source officielle ? ».

## La règle qui gouverne toutes les autres

> **AUCUNE SOURCE NE PEUT ÊTRE LE MODÈLE IMPLICITE DU PRODUIT.**

Elle se vérifie en une commande, qui **exécute** le moteur au lieu de relire
le code :

```
python3 outils/audit_biais.py --detail
```

Seize détecteurs. Le même besoin commercial est présenté sous **huit formes**
— avis public, page d'entreprise, recherche web, bourse de fret,
sous-traitance, partenariat, renouvellement, signal — avec la même économie et
les mêmes exigences. Ce qui **peut** changer : la source, la fiabilité, la
nature, l'état, l'action. Ce qui ne change **jamais** : le score économique,
l'analyse de capacité, la classification métier.

Il mesure aussi ce qu'aucun test unitaire ne mesure : le radar reste **entier**
avec 0 marché public, entier avec 0 donnée privée, et survit au retrait de
n'importe quel capteur pris un par un. Un capteur inédit, aux noms de champs
inventés, obtient exactement le même traitement — sans qu'une ligne du moteur
change.

## Ce que le radar sait dire — y compris « non »

Cinq catégories pour ce qui vaut quelque chose, et une sixième pour ce qui
n'en vaut pas — **encore** :

| | |
|---|---|
| 🟢 DIRECT | exécutable avec la structure actuelle |
| 🟡 RENFORCEMENT | possible après location ou recrutement |
| 🟣 À CONSTRUIRE | métier nouveau, accessible par montée en compétence |
| 🔵 PROSPECT | pas un contrat aujourd'hui, une porte d'entrée |
| ⚪ PAS ENCORE UNE OPPORTUNITÉ | lue, comprise, aucun fait commercial à cette date |
| 🔴 REJET | motivé — fourniture, activité exclue, hors zone |

⚪ n'est **pas** 🔴. « Notre société change son logo » n'est pas une affaire
aujourd'hui ; rien ne dit que cette société n'aura pas de besoin demain. Cette
catégorie n'existe que parce qu'une **vraie page** l'a rendue nécessaire : le
radar la classait 🔵 PROSPECT avec un score de 24/100 et l'action
« SURVEILLER ». Voir `validation/PREMIERE-MESURE-REELLE.md`.

## Huit formes de besoin, un seul moteur

| Ce que le radar voit | Ce que ça devient |
|---|---|
| marché public européen — distribution de colis, 36 mois | opportunité |
| rubrique « Marchés en cours » d'un portail d'acheteur | opportunité, après lecture de l'état |
| rubrique « Avis de préinformation » | futur besoin → DÉVELOPPER |
| rubrique « Appels à projets » | analyse propre : objet, bénéficiaire, conditions |
| marché public belge sous le seuil | opportunité |
| « nous recherchons un partenaire transport » trouvé par un moteur | opportunité |
| page « devenir partenaire transporteur » d'une PME | opportunité |
| « ouverture d'un centre logistique à Gand » | signal |
| recrutement simultané de 15 chauffeurs | signal |
| tournée régulière compatible sur une bourse de fret | opportunité |
| marché de 3 ans attribué à un tiers | piste DÉVELOPPER |
| métier nouveau avec formation assurée au démarrage | 🟣 à analyser |

Aucune n'est secondaire parce qu'elle n'est pas un appel d'offres.

```bash
python3 outils/radar_commercial.py   # les huit, dans le même moteur, un seul rapport
```

## Douze familles de besoin — l'appel d'offres en est une

```bash
python3 outils/familles.py            # les douze, dans le même moteur
python3 outils/familles.py --prive    # sans aucune source publique
python3 outils/familles.py --public   # sans aucune source privée
```

| famille | ce que c'est |
|---|---|
| `besoin_prive` | une entreprise qui cherche un transporteur |
| `besoin_public` | un marché belge sous le seuil |
| `sous_traitance` | un opérateur qui cherche des sous-traitants |
| `partenariat` | un réseau qui ouvre son référencement |
| `entreprise_a_demarcher` | une société dont la flotte sature |
| `signal_economique` | l'ouverture d'un centre logistique |
| `emploi_signal` | 25 chauffeurs recherchés |
| `attribution` | un marché de 2,9 M€ gagné par un tiers |
| `preinformation` | un besoin annoncé pour 2027 |
| `appel_offres` | un marché européen ouvert |
| `lot` | un marché à trois lots, trois états |
| `metier_inconnu` | des bornes de recharge, formation assurée |

Les trois lots — douze familles, privé seul, public seul — se réconcilient
tous à zéro. Retirer n'importe laquelle des douze ne casse rien : c'est testé
famille par famille.

**Le banc d'essai lui-même a été redressé.** Mesuré : `opp()` portait
`type_avis="appel-offres"` et `cpv=["60000000"]`, donc **94 % des opportunités
construites dans les tests étaient en forme de marché public**. Le moteur était
indépendant, mais son banc d'essai lui apprenait implicitement « opportunité =
marché public » — et un défaut n'apparaissant que sur une source privée serait
passé inaperçu. Le défaut est maintenant un besoin nu ; les tests qui ont
vraiment besoin d'un marché public le disent avec `avis_public()`.

---

## Symétrie public / privé — trois asymétries corrigées

Le cœur ne doit donner aucun privilège à une source officielle. Trois entorses
trouvées à l'audit, toutes silencieuses :

| asymétrie | ce qu'elle coûtait | correction |
|---|---|---|
| le lexique prestation/fourniture était écrit en langue de marchés publics | « nous recherchons un transporteur » → `A_VERIFIER`, alors qu'un avis équivalent → `PRESTATAIRE` grâce à son CPV | le lexique parle aussi la langue du privé (FR/NL/EN) |
| le **CPV** entrait dans l'empreinte de déduplication | le même besoin, public d'un côté et privé de l'autre, ne se reconnaissait pas — fusion `PROBABLE` au mieux, aucune si la formulation variait | le CPV sort de l'empreinte ; il redevient un garde-fou (`cpv_incompatible`) quand les **deux** côtés en portent un |
| la boucle étiquetait tout résultat web « google » | un résultat Brave faussait le rendement par source et rendait Google indispensable dans les chiffres | l'adaptateur s'appelle `recherche` ; la provenance reste celle du moteur qui a répondu |

Le cœur est vérifié par l'AST : **aucun module métier n'importe un adaptateur,
et aucun ne nomme un portail dans son code exécutable** (les commentaires
peuvent citer TED en exemple, le code non).

```bash
python -m unittest tests.test_radar.LeCoeurIgnoreLesCapteurs
python -m unittest tests.test_radar.MemeBesoinSixCapteurs
```

Le même besoin injecté depuis `ted · bda · tenderned · recherche · entreprise ·
bourse_fret` donne la même classification, la même capacité, le même score, le
même rôle, le même état — et **une seule opportunité** après déduplication,
avec les six provenances conservées. Retirer n'importe lequel des six ne casse
rien : c'est testé capteur par capteur.

---

## Quatre dimensions, jamais mélangées

Une annonce n'a pas « un statut ». Elle a quatre choses distinctes, et les
confondre produit les erreurs les plus coûteuses du radar.

| | | |
|---|---|---|
| **A · TYPE D'INFORMATION** | ce que le portail appelle l'objet | « Marchés en cours », « Avis de préinformation », « Appels à projets », « Résultats » |
| **B · ÉTAT DE PROCÉDURE** | où en est la procédure | `POSTULABLE` `ANNONCÉ` `ATTRIBUÉ` `FERMÉ` `ANNULÉ` `INFRUCTUEUX` `INFORMATIF` `INCONNU` — et `HORS PROCÉDURE` quand il n'y en a pas |
| **C · NATURE** | ce que vaut l'information | `FAIT` `SIGNAL` `HYPOTHÈSE` |
| **D · ACTION** | ce que je fais demain matin | POSTULER · CONTACTER L'ACHETEUR · CONTACTER LE TITULAIRE · SURVEILLER · VÉRIFIER L'ÉTAT |

`procedure.py` ne produit que **B**, et les preuves qui l'ont fait choisir.

### Comprendre, pas reconnaître des mots

Ce que le moteur ne fait **jamais** :

```
si le texte contient « attribué » → ATTRIBUÉ, sinon → POSTULABLE
```

Ce serait faux à peu près partout. « Aucun soumissionnaire n'a encore été
désigné » contient le vocabulaire de l'attribution et dit l'inverse. Un
document annexe nommé « avis d'attribution » ne dit rien de la page analysée.
Une date limite dépassée ne prouve **aucune** attribution — seulement qu'on ne
peut plus déposer.

Le moteur travaille donc sur des **concepts**, déclinés en FR/NL/EN/DE, et sur
leur composition : négation, futur, attente.

| lu sur la page | conclu |
|---|---|
| « consultations ouvertes » · « inschrijving mogelijk » · « Angebote können eingereicht werden » | POSTULABLE |
| « fournisseur retenu » · « gunning » · « der Zuschlag wurde erteilt » | ATTRIBUÉ |
| « les offres ne sont plus acceptées » · « procédure clôturée » | FERMÉ |
| « le marché sera attribué prochainement » | **pas** ATTRIBUÉ — annoncé, non prononcé |
| « aucun soumissionnaire n'a encore été désigné » | ni ATTRIBUÉ, ni POSTULABLE |
| « sélection en cours » | ni ATTRIBUÉ, ni POSTULABLE |
| date limite dépassée, rien d'autre | FERMÉ — **attribution NON PUBLIÉE** |
| « les soumissions peuvent encore être introduites » | POSTULABLE |
| « avis de préinformation » | **ANNONCÉ** — le besoin existe, la procédure pas encore |
| « phase gamma » | INCONNU, mémorisé pour être tranché |

### La hiérarchie des preuves — et sa limite

```
statut officiel déclaré  >  état explicite  >  rubrique du portail
                         >  formulation indirecte  >  dates  >  inférence
```

**Configurable par source** : un portail dont les rubriques sont notoirement en
retard peut les rétrograder sous les dates, dans son seul adaptateur, sans que
le moteur connaisse ce portail.

```yaml
procedure:
  hierarchie:
    rubrique: 0      # ce portail met ses listings à jour trop tard
```

**Sa limite — la zone de force égale.** La hiérarchie départage des preuves
*non contradictoires*. Elle ne fait pas gagner un champ structuré périmé contre
une phrase qui dit l'inverse :

```
statut structuré = POSTULABLE  +  texte « la procédure est clôturée »
→ INCONNU · CONTRADICTION À VÉRIFIER
```

Deux preuves de confiance ÉLEVÉE qui s'excluent ne produisent **aucun**
gagnant, quel que soit leur rang. Un portail n'est pas la vérité : sa rubrique
peut être en retard, son champ mal renseigné, sa page de résultat mise à jour
après coup.

Une annonce rangée dans « Marchés en cours » dont le texte dit « la procédure
est clôturée » ressort **FERMÉ** : la rubrique est un classement de listing,
souvent en retard ; la phrase parle de *cette* procédure. La contradiction
reste affichée sur la fiche :

```
ÉTAT          🟠 FERMÉ — candidature terminée — attribution non publiée
TYPE (source) Marchés en cours
CONFIANCE     faible
PREUVE        [état de procédure explicite] « description : « cloturee » » → FERMÉ
CONTRADICTION rubrique du portail dit POSTULABLE — écarté par « cloturee »
```

Deux preuves de même rang qui se contredisent ne produisent pas un gagnant
arbitraire : elles produisent `INCONNU`.

### INCONNU n'est jamais promu

`INCONNU` ne devient jamais `POSTULABLE` par défaut. L'opportunité reste dans
le radar avec l'action **VÉRIFIER L'ÉTAT À LA SOURCE** — ni jetée, ni promue.
Et si la source publie un statut que l'adaptateur ne sait pas lire, une date
future ne suffit pas à conclure : ce serait substituer notre calcul à sa
déclaration.

### Le vocabulaire s'apprend, il ne s'invente pas

Chaque `sources/*.yaml` déclare les valeurs **réellement observées** sur son
portail, avec leur sens et leur niveau de confiance. Une valeur absente ne
devient pas postulable par ressemblance : elle est mémorisée en base.

```bash
python -m radar.cli vocabulaire     # ce qui reste à trancher, avec son contexte
python -m radar.cli vocabulaire --trancher portail statut "phase gamma" ferme \
    --motif "vérifié sur le portail" --par hicham
```

Une révision **archive** l'ancienne lecture au lieu de l'effacer, et
**incrémente une version** : les fiches produites avec la version fausse
doivent rester retrouvables. Ce qu'un humain écrit dans le YAML prime toujours
sur ce que la mémoire a retenu.

**Le recalcul est contrôlé, jamais silencieux.** Trancher affiche d'abord les
opportunités concernées ; `--recalculer` les rejoue depuis le brut conservé et
montre lesquelles changent d'état :

```
1 fiche(s) changent d'état :
  POSTULABLE   → FERMÉ        SURVEILLER   Consultation — reprise des tournées

Ces transitions sont marquées « révision de vocabulaire » :
le marché n'a pas bougé, c'est notre lecture qui a changé.
Aucune alerte commerciale n'a été émise.
```

**Une expression tranchée sur un portail ne se propage jamais à un autre.**
« phase active » peut vouloir dire POSTULABLE ici et autre chose ailleurs.

### Lot par lot

Un marché parent `ATTRIBUÉ` dont le lot 3 est encore ouvert produit **trois
situations distinctes**, pas une seule fiche. Le statut du lot prime sur celui
du marché.

### Le rapport est le produit, pas un compteur d'avis

```
CAPTER                          ce que je peux attaquer maintenant
DÉVELOPPER                      titulaires, renouvellements, préinformations
SIGNAUX                         des événements, pas encore des contrats
À VÉRIFIER                      informations ambiguës, ni jetées ni promues
PAR FAMILLE DE BESOIN           besoins privés · marchés publics ·
                                sous-traitance · entreprises à démarcher ·
                                signaux · renouvellements · métiers à construire
TOP ACTIONS                     ce que je fais demain matin, groupé par geste
```

La famille se lit sur ce que l'opportunité **est** — son secteur, sa nature,
son état — jamais sur d'où elle vient : un besoin public trouvé par un moteur
de recherche va dans MARCHÉS PUBLICS, un besoin privé lu sur TED va dans
BESOINS PRIVÉS.

Les statistiques de collecte viennent **après**. Les sources y figurent comme
provenances (« vu sur »), jamais comme classement.

`SIGNAUX` sélectionne sur la **nature** (dimension C), surtout pas sur l'état
(dimension B) — le défaut trouvé en écrivant cette section. Une page qui dit
« devenir partenaire transporteur » est `HORS PROCÉDURE` sur B et un **FAIT**
sur C : la ranger parmi les signaux présenterait un fait comme une inférence.

```
« Nous recherchons un transporteur »              → FAIT
« L'entreprise recrute quinze chauffeurs »        → SIGNAL
« Elle aura probablement besoin de sous-traitants » → HYPOTHÈSE
```

### Une opportunité, un fil de vie

```
03/09 POSTULABLE  ·  14/09 FERMÉ  ·  28/09 ATTRIBUÉ
```

Ce n'est pas trois opportunités : c'est **une** opportunité, trois
observations, deux transitions. Une collecte qui ne change rien n'écrit rien —
sinon le fil de vie deviendrait un journal de passages du collecteur.

Chaque transition conserve `ancien → nouveau`, la preuve, la source, la date,
la confiance, l'origine et la version du vocabulaire.

### Les transitions sont des événements commerciaux

| transition | effet |
|---|---|
| POSTULABLE → FERMÉ | annule les alertes POSTULER **en attente** (silencieux) |
| FERMÉ → ATTRIBUÉ | récupère le titulaire, bascule en DÉVELOPPER |
| ANNONCÉ → POSTULABLE | ⚡ **LE MARCHÉ EST MAINTENANT OUVERT** |
| INFRUCTUEUX → POSTULABLE | ⚡ **NOUVELLE CHANCE DE POSTULER** |
| ANNULÉ → POSTULABLE | ⚡ **RELANCE APRÈS ANNULATION** |
| → INCONNU | aucune alerte : perdre la certitude n'est pas une occasion |

Le motif de l'alerte fait partie de la clé d'envoi : « je viens de la
découvrir » et « elle vient de s'ouvrir » sont **deux** événements, pas un
doublon.

**Et surtout** : une correction de notre vocabulaire n'est **jamais** présentée
comme un mouvement du marché. Les transitions d'origine `revision_vocabulaire`
n'émettent aucune alerte commerciale — le rapport les marque `✎` là où un vrai
changement porte `⚡`.

### Fiabilité de l'information ≠ valeur économique

Deux questions différentes, jamais mélangées :

```
« Combien ça peut rapporter ? »   → score.py
« À quel point j'en suis sûr ? »  → fiabilite.py
```

Une phrase trouvée sur le site d'une PME n'a ni référence, ni date, ni montant.
Sa fiabilité est faible ; sa valeur peut dépasser celle d'un marché public de
40 pages. Le radar la fait donc remonter **haut**, avec `FIABILITÉ : FAIBLE` et
`ACTION : VÉRIFIER` — jamais dévalorisée dans le score :

```
 score  fiabilité  action                   intitulé
    80  FAIBLE     CONTACTER L'ENTREPRISE   Tournée Rotterdam → Bruxelles
    73  FORTE      SURVEILLER               Préinformation — externalisation
```

`fiabilite.py` ne nomme aucune source — c'est vérifié par l'audit. Un avis TED
sans acheteur publié est moins fiable qu'une page d'entreprise qui nomme son
besoin, sa zone et son contact.

### L'état change l'action, jamais le score

```
POSTULABLE  → POSTULER            ATTRIBUÉ    → CONTACTER LE TITULAIRE
FERMÉ       → SURVEILLER          INFRUCTUEUX → CONTACTER L'ACHETEUR
ANNULÉ      → SURVEILLER          INFORMATIF  → SURVEILLER (futur marché)
INCONNU     → VÉRIFIER L'ÉTAT À LA SOURCE
```

Un marché fermé vaut économiquement ce qu'il vaut. Le score reste
CA × effort × investissement × risque × marge × adéquation — **testé** : les
quatre états ci-dessus, mêmes données par ailleurs, donnent le même score.

Aucun de ces états n'est un rejet. Un marché annulé est très souvent relancé ;
un marché infructueux signifie que l'acheteur cherche encore.

---

## Avant, pendant, après

Le radar couvre toute la chaîne commerciale, pas seulement le moment de l'avis :

```
AVANT     signal d'expansion → besoin probable → recherche de prestataire
          → contact commercial → (appel d'offres éventuel)
PENDANT   besoin publié → analyse → POSTULER / RENFORCER / PARTENARIAT
APRÈS     attribution → titulaire identifié → sous-traitance → renouvellement
```

Un portail de marchés ne montre que la colonne du milieu.

---

## Les trois mécanismes qui font la différence

### 1. Fourniture ou prestation ? (`role.py`)

Le piège le plus coûteux du marché public :

| Marché | Verdict |
|---|---|
| Fourniture et livraison de poissons frais | 🔴 l'acheteur veut du poisson |
| Fourniture et livraison de mobilier | 🔴 l'acheteur veut des meubles |
| Transport de produits pour le compte de l'hôpital | 🟢 la prestation EST l'objet |
| Déménagement de postes de soudure | 🟢 prestation |

L'entreprise vend une prestation, jamais un produit. Le CPV tranche en premier
parce qu'il est structuré ; le lexique n'arbitre qu'en son absence. Sans signal
exploitable : `A_VERIFIER`, jamais un verdict inventé.

### 2. Analyse lot par lot (`lots.py`)

Un marché n'est jamais rejeté sur son titre général.

```
« Fourniture, livraison et installation d'équipements »   ← titre : fourniture
   LOT 1  Fourniture de machines-outils                   🔴
   LOT 15 Déménagement de postes de soudure               🟢  ← le marché est retenu
```

Un seul lot compatible sauve le marché, et la fiche nomme lequel.

### 3. Trois niveaux de capacité (`capacite.py`)

| Exigence | Niveau | Verdict |
|---|---|---|
| 4 véhicules | ACTUELLE | ✔️ 6 en flotte |
| 12 véhicules | MOBILISABLE | 🔧 6 à louer, jusqu'à 16 |
| 25 véhicules | NON DISPONIBLE | 🔴 au-delà du mobilisable |
| AFSCA | ACTUELLE | ✔️ détenu |
| GDP | A_VERIFIER | 🟠 non confirmé — jamais présumé |
| ADR | NON DISPONIBLE | 🔴 une qualification ne se loue pas |

La capacité actuelle n'est pas la capacité maximale. Mais la mobilisation
couvre du matériel et des bras — pas un agrément.

---

## Les cinq catégories

| | Sens | Moteur |
|---|---|---|
| 🟢 **DIRECT** | exécutable avec la structure actuelle | CAPTER |
| 🟡 **RENFORCEMENT** | titulaire possible après location, recrutement, réorganisation | CAPTER |
| 🟣 **À CONSTRUIRE** | métier nouveau, formation réellement offerte, leviers existants | CAPTER |
| 🔵 **PROSPECT** | trop gros seul, signal privé, ou marché fermé à démarcher | CAPTER / DÉVELOPPER |
| 🔴 **REJET** | **jamais notifié** — seulement sur raison objective | — |

**La règle qui compte** : ce que je ne peux pas porter seul, un autre le portera
— il lui faudra des bras, donc 🔵. Ce que je ne sais pas faire, personne ne me
le sous-traitera, donc 🔴.

```
12 véhicules exigés  → 🟡 RENFORCEMENT  (6 à louer)
30 véhicules exigés  → 🔵 PROSPECT      (proposer une sous-traitance)
ADR exigé            → 🔴 REJET         (une qualification ne se loue pas)
```

### 🟣 — le test à six conditions

Un métier inconnu n'est jamais rejeté, mais une formation offerte ne suffit pas.
Les six conditions sont toutes obligatoires : levier d'actif réel, activité de
terrain, **formation écrite dans la source**, délai suffisant, aucune obligation
légale préalable manquante, cohérence économique.

```
Portes sectionnelles + formation 2 semaines   → 🟣
Portes sectionnelles sans formation           → non
Comptabilité + formation                      → hors périmètre
Installation + agrément obligatoire           → 🔴
```

## Deux moteurs

**CAPTER** — POSTULER · CONTACTER L'ACHETEUR · CONTACTER L'ENTREPRISE · PROPOSER
SOUS-TRAITANCE · PROPOSER PARTENARIAT.
**DÉVELOPPER** — CONTACTER LE TITULAIRE · SURVEILLER. Une attribution ne porte
jamais l'action POSTULER.

## Découverte Internet — niveau 1

Google cherche des **besoins**, pas des appels d'offres. Les requêtes sont
générées par croisement modèle × prestation × zone × langue — près de 2 000,
dont les locales passent en premier pour faire remonter les PME.

Sans clé : `NON DISPONIBLE — CLÉ ABSENTE`. Aucune simulation, aucun scraping des
pages de résultats.

```bash
export GOOGLE_API_KEY=...  GOOGLE_CSE_ID=...
python -m radar.cli requetes --limite 20
python -m radar.cli sources
```

## Un lot = une opportunité

Un marché à 20 lots produit une opportunité **par lot compatible**, chacune avec
sa référence, son montant, sa date, son score et son action. Le lien vers le
marché parent est conservé pour éviter les doublons. Un lot sans montant propre
n'hérite pas de celui du marché : ce serait inventer une valeur.

---

## Le score sert la PME, pas le gros marché

| Contrat | Score |
|---|---|
| 8 000 €/mois sur 24 mois, tournée quotidienne | **100** |
| 300 000 € avec 6 véhicules à louer | 84 |
| 5 000 000 €, CA de 2 M€ exigé | **78** |

Le marché à 5 M€ perd sur la taille (hors gabarit en titulaire direct) et sur la
concurrence probable. Toutes les pondérations sont dans
`config/ponderations.yaml`. Chaque point est justifié.

Le score **classe**, il n'élimine pas : les exigences bloquantes vivent dans
`capacite.py`, séparément, comme demandé.

---

## Géographie : un corridor, pas un pays

```
COLLECTE EUROPE → TRANSPORT → DÉPÔT BELGE → TRI → DISTRIBUTION BELGIQUE
```

| Flux | Verdict |
|---|---|
| NL → BE | 🟢 corridor, et déjà exécuté |
| PL → BE, ES → BE | 🟢 toute l'Europe vers la Belgique |
| BE → BE | 🟢 national |
| FR → FR, ES → ES | 🔴 hors modèle |
| lieu non publié | 🟠 conservé, signalé |

---

## Architecture

```
SOURCE
   ↓
COLLECTE
   ↓
NORMALISATION
   ↓
DÉTECTION DU BESOIN                role.py · activite.py · lots.py
   ↓
ÉTAT DU BESOIN / DE LA PROCÉDURE   nature.py · procedure.py · transitions.py
   ↓
BESOIN COMMERCIAL
   ↓
FAISABILITÉ                        capacite.py · geographie.py · construction.py
   ↓
ÉCONOMIE                           score.py (marge, effort, récurrence, taille)
   ↓
SCORE
   ↓
CAPTER / DÉVELOPPER                classification.py
```

**Aucun étage après la collecte ne sait d'où vient le besoin.** `score.py` ne
contient ni le mot `source`, ni `type_avis`, ni le nom d'un portail — c'est
vérifié par l'audit. Ajouter une source, c'est un fichier YAML ; ça ne touche
jamais au moteur.

| Fichier | Rôle |
|---|---|
| `profil.yaml` | l'entreprise, ses trois niveaux de capacité, sa cible économique |
| `config/roles.yaml` | fourniture contre prestation |
| `config/capacites.yaml` | ontologie métier, 11 familles, vocabulaire FR/NL/EN |
| `config/geographie.yaml` | le corridor |
| `config/ponderations.yaml` | les poids du score |
| `config/sources.yaml` | catalogue : pourquoi, ce qu'elle apporte, filtre, classement, déduplication |
| `sources/*.yaml` | un adaptateur par capteur — TED, BDA, portail d'acheteur, moteur de recherche, page d'entreprise, signaux, bourse de fret — chacun avec **son** vocabulaire de procédure |

**Aucune source n'a de priorité déclarée** : toutes les `priorite_initiale`
valent `null  # NON MESURÉE`. La priorité se calcule sur le rendement observé —
opportunités retenues, contacts obtenus, contrats gagnés, rapportés au volume
lu. Une source qui publie mille avis et n'en produit aucun d'exploitable passe
derrière une page d'entreprise qui en produit deux.

**Volume ≠ valeur.** Et une source jamais consultée n'a pas un mauvais
rendement : elle affiche `NON MESURÉE`, jamais `0`.

---

## Les seize questions

Avant toute notification, `questions.py` répond aux seize questions de la règle
absolue et consigne le journal en base. Ce qui ne peut pas être répondu vaut
`A_VERIFIER` — jamais une réponse inventée.

---

## Trois garde-fous d'intégrité

### DEMO ≠ RÉEL — structurellement

Deux bases distinctes (`radar-demo.sqlite3` / `radar-reel.sqlite3`), un bandeau
sur chaque sortie, et surtout : **en mode RÉEL, une ligne sans preuve de collecte
est refusée**. La preuve — source, URL ou identifiant réel, horodatage, empreinte
du contenu — n'est posée que par les collecteurs, au moment où la donnée arrive
du réseau. Une fixture n'en porte pas.

```
$ radar --reel traiter --source ted --entree exemples/marches.json
  brutes                         9
    dont illisibles         -9     MODE RÉEL : enregistrement sans preuve de collecte
  = CAPTER                       0
```

Ce que ça garantit : la **confusion** est impossible. Ce que ça ne garantit pas :
quelqu'un qui fabriquerait délibérément un bloc de collecte complet passerait.

### Le livre de comptes

Aucune opportunité ne disparaît en silence. Les totaux doivent se réconcilier,
sinon le cycle **échoue** :

```
brutes 9 → normalisées 9 → +2 lots → 11 → -4 rejets (ventilés) → CAPTER 6 + DÉVELOPPER 1
réconciliation ✔ exacte
```

Le bug des sept opportunités perdues déclencherait aujourd'hui :
`ERREUR — 7 opportunité(s) perdue(s) sans motif`.

### Déduplication à trois niveaux

| Niveau | Déclencheur | Effet |
|---|---|---|
| **CERTAIN** | référence officielle ou URL identiques | fusion automatique |
| **PROBABLE** | même acheteur + objet ≥ 75 % + même échéance | fusion tracée |
| **POSSIBLE** | similarité sémantique seule | **aucune fusion** — relié, `À VÉRIFIER` |

Deux fiches en double coûtent trente secondes. Une opportunité fusionnée à tort
ne revient jamais.

## Moteurs de recherche interchangeables

Le métier ne connaît aucun moteur en particulier :

```
SEARCH_PROVIDER → RÉSULTATS WEB → NORMALISATION → ANALYSE
```

Google et Brave implémentent le même contrat ; un moteur futur s'ajoute sans
qu'une ligne du moteur commercial change. Sans clé, chacun dit pourquoi il ne
peut rien faire — et **le radar tourne quand même sur ses autres sources**.

## Rendement par source — NON MESURÉE ≠ 0

```
SOURCE                 OBSERVÉ   PERTINENTES    CAPTER  DÉVELOPPER
ted                  NON MESURÉE   (JAMAIS CONSULTÉE)
bda                  NON MESURÉE   (JAMAIS CONSULTÉE)
google               NON MESURÉE   (NON DISPONIBLE — CLÉ ABSENTE)
```

Une source non consultée n'est pas classée dernière : son rendement est
**inconnu**. La priorité se recalcule ensuite sur ce qui est observé, jamais sur
la notoriété.

## Utilisation

```bash
# 0ter. Le radar sur huit formats de besoin, sans aucun réseau
python3 outils/radar_commercial.py

# 0bis. Répéter le trajet complet AVANT (aucun réseau nécessaire)
python3 outils/repetition_pipeline.py

# 0. Collecter de vraies réponses — depuis une machine ayant un accès réseau
python3 outils/collecter_ted.py --pages 20 --sortie reponses.json

# 1. MESURER avant de conclure
python -m radar.cli recenser --source ted --echantillon reponses.json
python -m radar.cli sonder   --source ted --entree     reponses.json

# 2. Traiter
python -m radar.cli --base radar.sqlite3 traiter --source bda --entree lot.json

# 3. Consulter (base ouverte en LECTURE SEULE, incapable d'écrire)
python -m radar.cli --base radar.sqlite3 opportunites --complet
python -m radar.cli --base radar.sqlite3 opportunites --type sous_traitance
python -m radar.cli --base radar.sqlite3 calendrier
python -m radar.cli --base radar.sqlite3 apprendre
```

---

## État — à lire avant de s'en servir

Tous les `sources/*.yaml` portent **`verifie: false`**. Les chemins de champs y
sont **plausibles, PAS MESURÉS** : aucun accès réseau depuis l'environnement de
développement, donc aucune réponse réelle observée. `recenser` mesure la
présence réelle de chaque clé ; tout champ à 0 % désigne une clé inexistante, à
corriger **dans le YAML, jamais dans le code**.

`sonder` mesure le marché public **et privé** et écrit `NON MESURÉ` partout où
l'observation manque. Sous 30 opportunités il refuse de publier un pourcentage.
`apprendre` ne conclut rien sous 10 observations.

**Aucune statistique de ce dépôt n'est inventée.**

---

## Avant les vraies données : la répétition générale

Un fichier réel est sale. Un montant écrit « 120 000 », une durée écrite
« douze », un avis sans identifiant, un enregistrement hors schéma : chacun de
ces cas a déjà fait perdre des lignes sur le projet précédent.

```bash
python3 outils/repetition_pipeline.py   # code non nul si une ligne se perd
```

La répétition fait passer **17 enregistrements volontairement hostiles** par la
chaîne entière et exige que le livre de comptes tombe juste à l'unité près.
Elle ne mesure PAS le marché et le dit en tête de sa sortie : c'est le chemin
qui est éprouvé, pas l'offre.

Elle a déjà trouvé cinq défauts avant qu'aucune donnée réelle n'arrive — dont
un lot exigeant douze véhicules que le moteur déclarait « exécutable avec la
structure actuelle ». Le détail de chacun, avec la règle concernée et le test
ajouté, est dans **[`VALIDATION-PREMIERE-SOURCE.md`](VALIDATION-PREMIERE-SOURCE.md)**, qui décrit aussi
la séquence exacte du jour où un premier flux RÉEL arrivera — d'où qu'il
vienne.

Règle posée d'avance : si les vraies données révèlent une mauvaise
classification, **le score n'est pas ajusté pour faire apparaître le résultat
attendu**. Sept éléments sont produits — donnée source, ce que le moteur a
compris, classification obtenue, pourquoi elle est fausse ou juste, règle
concernée, correction, test de non-régression.

---

## Le cahier des charges est vérifiable

Cinquante et une règles ont été validées puis verrouillées. Une règle peut se perdre lors
d'une réécriture — c'est arrivé une fois, les seize questions ont tourné sans
test pendant plusieurs versions. L'audit le détecte :

```bash
python3 outils/audit_cahier.py     # code non nul si une règle faiblit
```

Il rend quatre colonnes, pas un compteur :

```
RÈGLE                                    MÉCANISME               TEST  ÉTAT
deux preuves fortes contradictoires…     procedure._trancher      2/2  ✅ couvert
fiabilité ≠ valeur économique            fiabilite.evaluer        3/3  ✅ couvert
```

Le **mécanisme** nomme un symbole précis (`module.Classe.methode`), pas
seulement un fichier : un module qui existe mais dont la fonction a été
renommée lors d'une réécriture ressort ❌, même si des tests passent autour.
Une règle dont un seul test manque est ⚠️, jamais ✅ arrondi vers le haut.

*« 253 tests, tous verts » ne veut rien dire. Le nombre de tests n'est pas
l'objectif.*

## Tests

```bash
python -m unittest discover -s tests
```

299 tests de comportement. Aucun ne vérifie qu'une ligne de code existe :
chacun pose une question dont la mauvaise réponse coûte un contrat.

Zéro dépendance hors PyYAML.
