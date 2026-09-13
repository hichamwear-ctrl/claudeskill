# PLAN ÉTAPE 8 — MOTEUR DE DÉCOUVERTE WEB

Date : 2026-09-13 · **Aucun fichier modifié** · État de référence : `09e73d0`, 819 tests verts

---

## A. OBJECTIF EXACT

Permettre au radar de **découvrir ce qu'il ne connaît pas** : des entreprises
absentes du registre, des pages absentes de `pages_surveillees`, des besoins
absents des sources déclarées.

Et **rien d'autre**. La découverte alimente la chaîne existante ; elle ne
produit jamais d'opportunité par elle-même.

    URL DÉCOUVERTE  ≠  PAGE COLLECTÉE  ≠  CONTENU ANALYSÉ  ≠  OPPORTUNITÉ

Un titre de résultat de recherche n'est pas une preuve. C'est un **indice**, au
même titre qu'un libellé de lien en 7a — et 7a a précisément établi qu'un
indice ne promeut pas.

---

## B. ARCHITECTURE CIBLE

### B.1 Ce qui existe déjà et qu'il ne faut PAS refaire

| Élément | État |
|---|---|
| `MoteurRecherche` — `disponible` · `motif_indisponibilite` · `rechercher()` | ✅ construit |
| `Registre` de moteurs, ordre d'essai sans pondération | ✅ construit |
| `Resultat(titre, url, extrait, requete, fournisseur, consulte_le)` | ✅ construit |
| `Generateur` — **2 203 requêtes**, 6 familles, 12 zones, 3 langues | ✅ construit |
| `Boucle.parcourir(chercher, analyser)` — ne connaît aucun moteur | ✅ construit |
| Tables `requetes`, `sources`, `provenances` (+ `circuit`) | ✅ construites |
| `pages_surveillees` (statut, qualification), `entreprises` (identité) | ✅ construites |
| Collecte directe, robots.txt, détection de changement | ✅ construites |

**Les 2 203 requêtes couvrent déjà les treize signaux demandés** :

| Famille | Requêtes | Couvre |
|---|---|---|
| `besoin_explicite` | 717 | transporteur / sous-traitant / partenaire recherché |
| `secteur_zone` | 544 | livraison · distribution · logistique par zone |
| `signal_indirect` | 393 | recrutement massif · ouverture de dépôt · nouveau site |
| `referencement` | 274 | référencement fournisseur, besoin de capacité |
| `investissement_expansion` | 155 | expansion · nouveau contrat |
| `metier_a_construire` | 120 | capacités à développer |

Le renouvellement et l'attribution à développer viennent des **attributions**
(table `attributions` + `titulaires`), pas d'un moteur — ils sont déjà couverts.

### B.2 Ce qui manque, et c'est peu

**1. Un moteur réellement joignable et autorisé.** Voir §D — c'est le seul vrai
blocage, et il n'est ni architectural ni conceptuel.

**2. Trois manques dans le contrat de résultat :**

- `rang` — la place du résultat dans la liste rendue. Sert au **diagnostic de
  capteur** et aux métriques de rappel. **Jamais au score.**
- `page_source` — quand une URL vient d'une page lue plutôt que d'un moteur.
- un **état de collecte** porté par l'URL découverte elle-même : une URL rendue
  par un moteur n'a **pas** été consultée par le radar.

**3. Une table `decouvertes`** — le journal des URL vues, avant toute collecte.
Aujourd'hui une URL découverte devient immédiatement une `page_surveillee`
CANDIDATE. C'est acceptable, mais cela mélange deux choses : *« un moteur m'a
montré cette URL »* et *« j'ai décidé de la suivre »*. Le second dérive du
premier ; il ne s'y substitue pas.

**4. Un moteur de FIXTURE** implémentant `MoteurRecherche` et lisant un fichier
local. C'est la seule façon de construire et prouver l'étape 8 **sans réseau**,
comme le projet l'a fait pour chaque page réelle depuis le début. Il devra être
structurellement impossible de le confondre avec un moteur réel : nom explicite
`fixture`, mode DEMO obligatoire, refus en mode RÉEL.

### B.3 Neutralité de source — le point non négociable

```
pertinence.evaluer(texte, ontologie, detecteur)      ← aucun paramètre source
score.py · classification.py                          ← 0 occurrence de « circuit »
liens.py · pages.qualifier()                          ← aucune source
```

C'est déjà vérifié par tests depuis 7a/7b. **L'étape 8 ne doit rien y changer.**
Le moteur d'origine entre dans la **provenance** et les **métriques**. Jamais
dans le score. Une affaire trouvée par un moteur de fixture, par Brave, par le
BDA ou en revisitant une page connue vaut exactement pareil.

---

## C. INVENTAIRE DES FAMILLES DE SOURCES

Sept familles, et elles ne font pas la même chose.

### C.1 Moteur de recherche généraliste (index du web entier)

**Permet** : découvrir des entreprises et des pages totalement inconnues, dans
les trois langues, sur toute la Belgique.
**Ne permet pas** : lire les pages — un moteur rend un titre, une URL, un
extrait. Rien de plus.
**Candidats** : Google Web Search (fermé), Bing Web Search (retiré 2025-08-11).

### C.2 API de recherche indépendante

**Permet** : la même chose avec un index propre — donc un **rappel réellement
différent**, ce qui est l'argument principal du multi-moteurs.
**Candidats** : Brave, Exa, Tavily, SerpAPI, Serper, Mojeek.
**Contrainte majeure** : la plupart interdisent contractuellement de **stocker**
ou d'**indexer** les résultats sans un plan accordant ces droits.

### C.3 Moteur limité à des domaines

**Permet** : chercher dans une liste de sites qu'on a déjà.
**Ne permet pas** : **découvrir l'inconnu** — par construction.
**Candidats** : Google PSE (≤ 50 domaines pour les nouveaux moteurs), Agent
Search ex-Vertex (« web domains that it owns or is authorized to utilize »).
**Verdict** : utile pour la **surveillance**, inutile pour la **découverte**.
Ce n'est pas une solution de repli, c'est un autre métier.

### C.4 Recherche directe sur un site connu

**Permet** : trouver de nouvelles **pages** d'une entreprise **déjà connue** —
via son `sitemap.xml`, sa navigation, ses liens.
**Ne permet pas** : découvrir une entreprise inconnue.
**Accès** : aucun moteur requis. robots.txt obligatoire.
**Déjà construit** en 7b/7c (`liens.selectionner`, `pages.depuis_liens`).

### C.5 Collecte de pages autorisée

**Permet** : lire réellement une URL connue.
**Ne permet pas** : la trouver.
**Déjà construit** : `collecte_directe.recuperer()`.
C'est le **complément indispensable** de toute découverte : sans lui, une URL
découverte reste un titre.

### C.6 Signaux découverts indirectement

**Permet** : voir bouger une entreprise sans qu'elle publie d'annonce —
Moniteur belge (créations, sièges), BCE/KBO (activité NACE), comptes annuels,
offres d'emploi massives, presse économique locale.
**Ne permet pas** : donner un besoin explicite. Un signal **n'est pas** une
opportunité — invariant déjà gelé.
**Intérêt** : c'est le seul chemin qui découvre une entreprise **avant** qu'elle
publie quoi que ce soit.

### C.7 Sources publiques spécialisées

**Permet** : des besoins explicites, structurés, avec titulaire, montant, durée.
**Ne permet pas** : le privé, qui est l'essentiel du marché visé.
**Candidats** : TED, e-Procurement belge, BOAMP.
**Déjà branchés** côté adaptateurs (`ted.yaml`, `bda.yaml`) — il manque l'accès.

---

## D. MATRICE — QUATRE DIMENSIONS, JAMAIS MÉLANGÉES

> **TECHNIQUEMENT POSSIBLE** ≠ **ACCESSIBLE ICI** ≠ **AUTORISÉ POUR NOTRE USAGE** ≠ **PERTINENT**

Joignabilité **mesurée le 2026-09-13**, depuis ce conteneur.

| Piste | Famille | Technique | Accessible ici | Autorisé | Pertinent | Découvre entreprise | Découvre page | Provenance | Statut |
|---|---|---|---|---|---|---|---|---|---|
| **Google Custom Search JSON** | C.1 | ✅ | ✅ hôte 404 | ❌ **fermé aux nouveaux clients** (403 mesuré) | ✅ | ✅ | ✅ | ✅ | 🔴 **NON AUTORISÉ** |
| **Google Grounding (Gemini)** | C.1 | ✅ | ✅ **chemin atteint, 400 clé** | ❌ **interdit** : « using Links to build an index » | ✅ | ✅ | ✅ | ⚠️ URL de redirection | 🔴 **NON AUTORISÉ** |
| **Google PSE** | C.3 | ✅ | ✅ | ✅ | ❌ 50 domaines | ❌ | ⚠️ | ✅ | 🔴 **NON ADAPTÉ** |
| **Agent Search (ex-Vertex)** | C.3 | ✅ | ✅ 404 | ⚠️ domaines possédés seulement | ❌ | ❌ | ⚠️ | ✅ | 🔴 **NON ADAPTÉ** |
| **Bing Web Search v7** | C.1 | ❌ **retirée 2025-08-11** | — | — | ✅ | — | — | — | 🔴 **N'EXISTE PLUS** |
| **Grounding with Bing** | C.1 | ✅ | ❌ 000 | ❌ « not directly accessible for use in other applications » | ❌ texte généré | ❌ | ❌ | ⚠️ | 🔴 **BLOQUÉ + NON AUTORISÉ** |
| **Brave Search API** | C.2 | ✅ index propre | ❌ **000** | ⚠️ **plan avec droits de stockage requis** | ✅✅ | ✅ | ✅ | ✅ | 🟠 **BLOQUÉ (egress)** |
| **Exa** | C.2 | ✅ | ❌ 000 | ❓ à lire à la source | ✅ | ✅ | ✅ | ✅ | 🟠 **BLOQUÉ** |
| **Tavily** | C.2 | ✅ | ❌ 000 | ❓ | ✅ | ✅ | ✅ | ✅ | 🟠 **BLOQUÉ** |
| **SerpAPI / Serper** | C.2 | ✅ | ❌ 000 | ⚠️ zone grise — revend un moteur tiers | ✅ | ✅ | ✅ | ✅ | 🟠 **BLOQUÉ + À ARBITRER** |
| **Mojeek / Stract** | C.2 | ✅ index propre | ❌ 000 | ❓ | ✅ | ✅ | ✅ | ✅ | 🔵 **À TESTER** |
| **DuckDuckGo HTML/Lite** | C.1 | ⚠️ | ❌ 000 | ❌ **automatiser l'interface grand public est contraire aux conditions** | — | — | — | — | 🔴 **NON AUTORISÉ** |
| **Common Crawl** | C.2 | ✅ archive ouverte | ❌ 000 | ✅ **licence ouverte** | ⚠️ ancien, volumineux | ✅ | ✅ | ✅ | 🔵 **À TESTER — piste sous-estimée** |
| **Sitemap / liens d'un site connu** | C.4 | ✅ | ⚠️ dépend de l'hôte | ✅ robots.txt | ✅ pages | ❌ | ✅ | ✅ | 🟢 **ARCHITECTURALEMENT PRÊT** |
| **Collecte directe** | C.5 | ✅ | ❌ hôtes cibles 000 | ✅ | ✅ | ❌ | ❌ | ✅ | 🟢 **CONSTRUIT** |
| **BCE/KBO open data** | C.6 | ✅ | ❌ 000 | ✅ open data | ✅✅ identité | ❌ | ✅ | ✅ | 🟠 **BLOQUÉ** |
| **Moniteur belge** | C.6 | ✅ | ❌ 000 | ✅ public | ✅ | ❌ | ✅ | ✅ | 🟠 **BLOQUÉ** |
| **TED / e-Procurement** | C.7 | ✅ | ❌ 000 | ✅ | ✅ public seulement | ⚠️ | ✅ | ✅ | 🟠 **BLOQUÉ** |
| **Moteur de FIXTURE** | — | ✅ | ✅ local | ✅ | ⚠️ **ne mesure aucun marché** | ✅ mécanisme | ✅ mécanisme | ✅ | 🟢 **DISPONIBLE** |

### Ce que la matrice dit

**Aucun moteur de découverte web n'est à la fois accessible, autorisé et
pertinent aujourd'hui.** Trois murs distincts, et ils ne se lèvent pas de la
même façon :

| Mur | Pistes concernées | Qui peut le lever |
|---|---|---|
| **Juridique** | Google Grounding, Bing Grounding, DuckDuckGo | l'éditeur seul |
| **Commercial** | Google Custom Search | personne — définitif |
| **Egress** | **Brave, Exa, Tavily, Mojeek, Common Crawl, BCE, Moniteur, TED** | **une liste blanche** |

**Le mur dominant est l'egress**, et c'est le seul purement technique.

### Deux pistes que je signale et que je n'ai pas assez pesées avant

- **Common Crawl** — archive web ouverte, licence permissive, index consultable
  par domaine. Elle ne donne pas la fraîcheur d'un moteur, mais elle permet de
  **découvrir des entreprises et des pages sans contrat commercial**. Statut
  réel : `À TESTER`, bloquée ici.
- **Mojeek** — index indépendant, API documentée. `À TESTER`, bloquée ici.

---

## E. FLUX EXACT

```
  REQUÊTE (Generateur, 2 203 prêtes)
      │
      ▼
  MOTEUR  ──── indisponible ? ──► source marquée NON DISPONIBLE, motif écrit
      │                            les autres circuits CONTINUENT
      ▼
  RÉSULTAT  titre · url · extrait · requête · fournisseur · rang · date
      │
      ▼
  DÉCOUVERTE ENREGISTRÉE          ◄── nouvelle table `decouvertes`
      url · source · requête · rang · vue_le
      ÉTAT DE COLLECTE = NON COLLECTÉE          ← rien n'a été lu
      │
      ├──► ENTREPRISE ?  nom identifiable → registre · identité INCONNUE
      │                  nom non identifiable → domaine seul, JAMAIS inventé
      │
      ▼
  PAGE CANDIDATE                  ◄── pages.rencontrer(), provenance + circuit
      │                               statut CANDIDATE (7b)
      ▼
  COLLECTE DIRECTE (facultative)  ◄── robots.txt, délai, aucun contournement
      │                               échec → ERREUR / NON DISPONIBLE
      │                               et le contenu reste INCONNU
      ▼
  QUALIFICATION SUR CONTENU RÉEL  ◄── pages.qualifier() (7b)
      │                               PREUVE / CONTRE-PREUVE / SANS PREUVE
      ▼
  NORMALISATION → CHAÎNE D'ANALYSE
      rôle · ontologie · état · nature · fiabilité · capacités
      │
      ▼
  DÉDUPLICATION par empreinte de BESOIN
      même besoin, deux moteurs → UNE opportunité, DEUX provenances
      │
      ▼
  CLASSIFICATION · SCORE · FICHE · SUIVI
```

**Le moteur de découverte s'arrête à la troisième boîte.** Tout ce qui suit
existe déjà et n'est pas redéfini.

---

## F. ÉCHECS ET SOURCES INDISPONIBLES

Les règles sont déjà en place et ne changent pas :

| Situation | Comportement | Interdit |
|---|---|---|
| aucun moteur | `BOUCLE NON LANCÉE` + motif de **chaque** moteur | « aucune opportunité » |
| moteur en erreur | source `ERREUR`, motif horodaté | rendre un résultat vide |
| quota épuisé | `NON DISPONIBLE` + motif | réessayer en boucle |
| URL découverte, page injoignable | `ERREUR` / `NON DISPONIBLE`, contenu `INCONNU` | « page inexistante » |
| robots.txt illisible | `NON DISPONIBLE`, abstention | passer outre |
| source jamais consultée | `JAMAIS CONSULTÉE` | compter 0 |

**`NON MESURÉ ≠ 0`** et **« moteur indisponible » = « DÉCOUVERTE WEB
INDISPONIBLE »**, jamais « pas d'affaires ». Les autres circuits continuent.

---

## G. MÉTRIQUES

Trois blocs qui **ne se mélangent jamais**, dans le prolongement de `radar circuits` (C9).

**DÉCOUVERTE** — requêtes exécutées · résultats reçus · **URL uniques** ·
uniques par moteur / communes à plusieurs · taux de déduplication · entreprises
nouvelles · pages candidates nouvelles · erreurs · quota restant.

**COLLECTE** — URL découvertes **non collectées** · pages réellement collectées
· pages illisibles · erreurs réseau · non disponibles (robots).

**QUALIFICATION → OPPORTUNITÉ** — pages qualifiées par verdict · doublons
fusionnés · opportunités générées · confirmées · rejetées avec motif ·
**faux positifs / faux négatifs identifiés**, tenus à la main.

**Rendement par moteur** — `Rendement.priorite()` existe déjà et part de
`NON MESURÉE` pour toutes les sources. Aucun moteur ne démarre avec un
avantage.

---

## H. STRATÉGIE DE RAPPEL ÉLEVÉ

```
  COLLECTE LARGE → ANALYSE LARGE → DÉDUPLICATION → CLASSIFICATION → SCORE → TOP
```

et **jamais** :

```
  COLLECTE ÉTROITE → SCORE → SUPPRESSION
```

Concrètement, cinq règles déjà en vigueur que l'étape 8 doit préserver :

1. **`mot absent → rejet` reste interdit.** Une requête qui ne rend rien ne
   rejette rien : elle mesure un rendement.
2. **Le score classe, il ne filtre pas.** Une opportunité à 10/100 reste visible.
3. **Une candidate n'est jamais supprimée** (7b).
4. **Un indice ne promeut pas** (7a) — un titre de résultat encore moins.
5. **La déduplication fusionne, elle n'efface pas** : les provenances
   s'additionnent.

Le tri se fait **après** l'analyse, jamais avant la collecte.

---

## I. PLAN DE TESTS

Tous avec un **moteur de fixture**, aucun réseau.

| # | Cas | Attendu |
|---|---|---|
| 1 | même besoin découvert par deux moteurs | **1 opportunité, 2 provenances**, 2 circuits |
| 2 | URL différente, même page (`?utm=`, `#`, `www.`) | **1 page**, URL normalisée |
| 3 | même entreprise découverte plusieurs fois | **1 fiche**, motifs cumulés |
| 4 | résultat de recherche sans accès à la page | découverte `NON COLLECTÉE`, **aucune opportunité**, contenu INCONNU |
| 5 | page accessible mais non commerciale | candidate, `SANS PREUVE`, conservée |
| 6 | page commerciale exploitable | qualifiée `PREUVE`, surveillée, opportunité par la chaîne |
| 7 | signal indirect (ouverture de dépôt) | entreprise au registre, **jamais** une opportunité directe |
| 8 | source indisponible | `NON DISPONIBLE` + motif ; les autres circuits continuent |
| 9 | source techniquement dispo, **non autorisée** | jamais interrogée, motif contractuel écrit |
| 10 | source autorisée, **inaccessible ici** | `ERREUR`/`NON DISPONIBLE`, jamais « rien trouvé » |
| 11 | **aucun moteur externe** | surveillance, sources directes, DÉVELOPPER, suivi : **tout continue** |
| 12 | le moteur de fixture en mode RÉEL | **refusé** — impossible de confondre fixture et réel |
| 13 | rang du résultat | présent en provenance, **absent du score** |
| 14 | même besoin par fixture et par source directe | même score, circuits différents |

---

## J. CE QUE JE PROPOSE DE CODER — ET CE QUE JE NE PROPOSE PAS

| | Chantier | Réseau requis | Prouvable aujourd'hui |
|---|---|---|---|
| **8a** | Table `decouvertes` + `rang` et `page_source` au contrat `Resultat` | non | ✅ |
| **8b** | Moteur de **fixture**, refusé en mode RÉEL | non | ✅ |
| **8c** | Chaînage découverte → entreprise → page candidate, avec provenance et circuit | non | ✅ |
| **8d** | Déduplication multi-moteurs + métriques de rappel | non | ✅ |
| **8e** | Connecteur d'un moteur réel | **oui** | ❌ **impossible** |

**Je ne propose pas 8e.** Écrire un connecteur qu'on ne peut ni exécuter ni
mesurer, c'est produire du code non prouvé — et le présenter comme une
capacité serait exactement ce que ce projet refuse depuis le début.

---

## K. INCERTITUDES ET DÉCISIONS QUI VOUS REVIENNENT

**1. `DÉCISION MÉTIER À VALIDER` — le moteur de fixture.**
Il permet de construire et prouver 8a-8d sans réseau. Mais il ne mesure **aucun
marché réel**. Acceptez-vous de construire l'étape 8 sur fixtures, en sachant
que la découverte restera `NON MESURÉE` tant que l'egress est fermé ?

**2. `DÉCISION MÉTIER À VALIDER` — quel moteur viser en priorité ?**
Ma lecture : **Brave** (index propre, droits de stockage achetables, connecteur
déjà écrit), puis **Common Crawl** (licence ouverte, aucun contrat). Mais les
deux sont bloqués par l'egress : le choix n'a d'effet qu'après ouverture.

**3. `DÉCISION MÉTIER À VALIDER` — SerpAPI / Serper.**
Ils revendent l'accès aux résultats d'un moteur tiers. La conformité repose sur
l'éditeur, pas sur nous. **Je ne trancherai pas cette question à votre place.**

**4. Question ouverte — une découverte non collectée doit-elle entrer au
registre des entreprises ?**
Un moteur rend « Transports Exemple SRL — exemple.be ». Sans avoir lu la page,
faut-il créer l'entreprise ? Mon avis : **oui, avec identité INCONNUE** — c'est
une rencontre, pas une affirmation. Mais cela remplira le registre de noms non
vérifiés. À arbitrer.

**5. Ce que je ne peux pas promettre.**
Je ne peux pas garantir qu'un moteur accessible existera. Je peux garantir que
l'architecture n'en dépendra pas — c'est ce que l'étape 7 a établi.

---

## L. CE QUE L'ÉTAPE 8 NE TOUCHERA PAS

`classification.py` · `score.py` · `procedure.py` · `fiche.py` · `portee.py` ·
`capacite.py` · `nature.py` · `suivi.py` · `ponderations.yaml` ·
`geographie.yaml` · `capacites.yaml` · `roles.yaml`.

Les catégories 🟢 🟡 🟣 🔵 ⚪ 🔴, les moteurs CAPTER/DÉVELOPPER et les cinq
dimensions déjà validées **ne sont pas redéfinis**.

Et les problèmes hors périmètre restent hors périmètre : « suivi de colis →
DIRECT », le seuil P2 de `liens.selectionner`, les composés néerlandais de
`capacites.yaml`.
