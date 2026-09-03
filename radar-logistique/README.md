# Radar commercial — transport et logistique

Pas un agrégateur d'appels d'offres. Un radar qui part de **l'entreprise** et
cherche partout des contrats qu'elle peut réellement décrocher **et exécuter**.

La question posée à chaque étage :

> Est-ce que cette entreprise peut réellement postuler ou obtenir ce contrat
> avec ses capacités actuelles, éventuellement en louant du matériel ou en
> travaillant avec un partenaire ?

Et jamais : « est-ce que cette annonce contient le mot transport ? »

TED et le BDA ne sont que deux sources parmi d'autres. Le noyau n'en dépend pas.

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
SOURCE → COLLECTE → NORMALISATION → MARCHÉ → LOTS → PRESTATIONS
       → GÉOGRAPHIE → EXIGENCES → CAPACITÉS → ÉLIGIBILITÉ
       → CLASSIFICATION → SCORE → DÉDUPLICATION → NOTIFICATION
```

Aucun étage après la collecte ne sait d'où vient l'opportunité. Ajouter une
source, c'est un fichier YAML.

| Fichier | Rôle |
|---|---|
| `profil.yaml` | l'entreprise, ses trois niveaux de capacité, sa cible économique |
| `config/roles.yaml` | fourniture contre prestation |
| `config/capacites.yaml` | ontologie métier, 11 familles, vocabulaire FR/NL/EN |
| `config/geographie.yaml` | le corridor |
| `config/ponderations.yaml` | les poids du score |
| `config/sources.yaml` | catalogue : pourquoi, ce qu'elle apporte, filtre, classement, déduplication |
| `sources/*.yaml` | un adaptateur par source |

Le catalogue met **le BDA en priorité 1 et TED en 3** : c'est dans les marchés
locaux que vivent les lots à taille de PME.

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

## Tests

```bash
python -m unittest discover -s tests
```

67 tests de comportement, un par règle du cahier des charges. Aucun ne vérifie
qu'une ligne de code existe.

Zéro dépendance hors PyYAML.
