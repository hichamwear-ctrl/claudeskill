# PLAN 8e — PREMIER MOTEUR RÉEL : ARBITRAGE ET ACCÈS

Date : 2026-09-13 · **Aucun code écrit, aucun moteur branché** · Référence `a82114c`, 934 tests verts

---

## AVERTISSEMENT MÉTHODOLOGIQUE — À LIRE AVANT LE TABLEAU

**Je n'ai pas pu lire les conditions d'utilisation à la source.** L'egress bloque
`api-dashboard.search.brave.com`, `commoncrawl.org`, `exa.ai`, `tavily.com`,
`serpapi.com` — pour le navigateur de l'assistant comme pour le conteneur.

Conséquence, et elle est sérieuse :

| Source | Statut de ma lecture |
|---|---|
| **Google** — `cloud.google.com/terms/service-terms` | ✅ **LU À LA SOURCE**, aujourd'hui, 1 018 343 octets |
| Brave, Exa, Tavily, SerpAPI, Serper, Common Crawl | ⚠️ **RAPPORTÉ PAR DES TIERS — À VÉRIFIER** |

Tout ce qui suit et qui n'est pas marqué « lu à la source » est **une
indication, pas une preuve**. Aucun contrat ne doit être signé sur cette base.

---

## A. LE CONSTAT QUI DOMINE TOUT LE RESTE

En lisant les conditions des uns et des autres, une même clause revient :

> **interdiction de stocker, mettre en cache ou constituer une base de données
> des résultats de recherche.**

Or `radar/trouvailles.py` est **exactement** cela : URL, titre, extrait, rang,
requête, date. C'est une base de données de résultats de recherche.

Ce n'est pas un détail d'implémentation. C'est **la contrainte structurante de
8e**, et elle n'était pas visible avant d'avoir construit 8a.

### Trois postures possibles — et c'est une DÉCISION MÉTIER

| | Posture | Ce qu'on conserve | Coût |
|---|---|---|---|
| **P1** | Conserver tout (état actuel) | URL · titre · extrait · rang · requête · date | exige un plan accordant des **droits de stockage** |
| **P2** | Ne conserver que l'**URL et la provenance** | URL · source · requête · rang · date — **sans titre ni extrait** | perd la matière de qualification à la découverte |
| **P3** | Ne rien conserver | — | perd l'historique, le recouvrement, l'apport par moteur — donc 8a et 8d |

**P3 annulerait 8a et 8d.** P2 est le compromis technique : une URL est un
fait, pas un contenu éditorial. Mais **je ne sais pas** si les éditeurs
considèrent une liste d'URL comme un « résultat de recherche stocké ».
→ **À VÉRIFIER auprès de chaque éditeur avant tout engagement.**

---

## B. GOOGLE — quatre voies, et je les ai lues

### B.1 Custom Search JSON API

| | |
|---|---|
| Recherche web large | ⚠️ pour les moteurs historiques seulement |
| Accès actuel | 🔴 **FERMÉ AUX NOUVEAUX CLIENTS** |
| **Preuve** | `403 PERMISSION_DENIED — « This project does not have the access to Custom Search JSON API »`, **reproduit depuis ce conteneur avec la clé et le `cx` de l'exploitant** |
| Notre environnement | ✅ `customsearch.googleapis.com` HTTP 404 — hôte joignable |
| Stockage | sans objet |
| Verdict | 🔴 **NON DISPONIBLE** — définitif, personne ne peut le lever |

### B.2 Programmable Search Engine

| | |
|---|---|
| Recherche web large | 🔴 **NON** — nouveaux moteurs limités à 50 domaines |
| **Preuve** | annonce Google de janvier 2026 · **À VÉRIFIER** (page bloquée ici) |
| Verdict | 🔴 **NON ADAPTÉ** — un moteur limité à des domaines ne découvre pas l'inconnu, par construction |

### B.3 Web Search Service API

| | |
|---|---|
| Existence | ❓ **ABSENT de l'annuaire des 530 API Google** — revérifié |
| **Preuve** | `websearchservice.googleapis.com` répond 404 par le joker `*.googleapis.com`, mais son document de découverte est introuvable et toutes les variantes de chemin rendent du **HTML 404**, là où une vraie API publique rend du **JSON 400** |
| Prérequis | `clientContext.clientId` — un « designated partner client ID » lié à un accord de partenariat |
| Coût / quota | **NON PUBLIÉ** |
| Verdict | 🔵 **VOIE PARTENAIRE — À DEMANDER**, délai inconnu |

### B.4 Grounding with Google Search

| | |
|---|---|
| Recherche web large | ✅ |
| Notre environnement | ✅ **chemin atteint** — `generativelanguage.googleapis.com` rend `400 API_KEY_INVALID`, donc seul la clé manque |
| Coût | **5 000 requêtes/mois sans frais, puis 14 $/1 000** — *lu sur la page tarifaire Google* |
| **Stockage / historique** | 🔴 **EXPLICITEMENT INTERDIT** |

**Clause lue à la source aujourd'hui, verbatim :**

> « it is a violation of these terms to use Grounding with Google Search to
> extract or collect one or more of these components for another purpose (for
> example, **using programmatic or automated means to collect Links, using
> Links to build an index, or using Links to identify destination pages for
> crawling or scraping**) »

Le radar collecte des liens par moyen programmatique, en construit un index, et
s'en sert pour identifier des pages à récupérer. **Les trois exemples cités par
la clause, littéralement.**

| Verdict | 🔴 **NON AUTORISÉ POUR NOTRE USAGE** — et c'est la seule voie Google dont l'interdiction soit certaine, parce que je l'ai lue |

### VERDICT GOOGLE

🔴 **Aucune voie Google n'est à la fois accessible, autorisée et pertinente.**
La seule techniquement ouverte est celle qui interdit explicitement notre usage.

---

## C. BRAVE SEARCH API

| | |
|---|---|
| Recherche web large | ✅ **index propre et indépendant** — c'est son intérêt principal : un rappel réellement différent de Google |
| Accès actuel | ✅ API publique, souscription en ligne |
| **Notre environnement** | 🔴 **`api.search.brave.com` HTTP=000** — refus de tunnel CONNECT par la passerelle, **mesuré aujourd'hui** |
| Stockage | ⚠️ conditions standard : *« shall not store, cache, or create a database of Search Results … other than transient storage »*. Un **plan accordant des droits de stockage** serait nécessaire. **RAPPORTÉ — À VÉRIFIER** |
| Coût | restructuration des plans en février 2026 ; crédit gratuit ~5 $/mois ≈ 1 000 requêtes. **À VÉRIFIER** |
| Rappel potentiel | ✅ élevé — index distinct |
| Adaptation radar | ✅ **connecteur déjà écrit** dans `moteurs_recherche.py` |
| Verdict | 🟠 **ACCESSIBLE SOUS CONDITIONS — BLOQUÉ PAR L'ENVIRONNEMENT** |

**Deux prérequis, et ils sont indépendants :** ouvrir l'egress vers un hôte ·
souscrire un plan avec droits de stockage **après avoir lu ses conditions**.

---

## D. LES AUTRES MOTEURS

| Solution | Web large | Accès | Environnement | Stockage autorisé | Coût | Rappel | Adaptation | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Exa** | ✅ index propre, sémantique | ✅ public | 🔴 **000 mesuré** | 🔴 *« forbids persistent caching … storing results in a database is data redistribution »* — **RAPPORTÉ, À VÉRIFIER** | ~7 $/1 000 · ~20 000/mois gratuits | ✅ | ✅ | 🔴 **NON AUTORISÉ POUR NOTRE USAGE** si confirmé |
| **Tavily** | ✅ | ✅ public | 🔴 **000 mesuré** | ❓ zéro rétention **de leur côté** ; rien de clair sur **le nôtre** — **À VÉRIFIER** | ~7,50-8 $/1 000 · 1 000 crédits/mois | ✅ | ✅ | 🟠 **ACCESSIBLE SOUS CONDITIONS** |
| **SerpAPI** | ✅ revend Google | ✅ public | 🔴 **000 mesuré** | ❓ **À VÉRIFIER** | ~25 $/1 000 | ✅ | ✅ | ⚠️ **À ARBITRER — LITIGE EN COURS** |
| **Serper** | ✅ revend Google | ✅ public | 🔴 **000 mesuré** | ❓ | — | ✅ | ✅ | ⚠️ **À ARBITRER** |
| **Mojeek** | ✅ index propre | ✅ | 🔴 **000 mesuré** | ❓ **À VÉRIFIER** | ❓ | ⚠️ index plus petit | ✅ | 🔵 **À TESTER** |

### SerpAPI / Serper — le fait juridique, sans interprétation

Google a assigné SerpApi en décembre 2025 (Californie, DMCA). En juillet 2026,
la demande DMCA a été **rejetée avec préjudice**. Google a annoncé un **recours
amendé**. **RAPPORTÉ — À VÉRIFIER.**

**Je ne tranche pas.** Ce que je constate : le litige oppose Google à
l'éditeur, pas à ses clients ; il n'est pas clos ; le droit applicable en
Belgique n'est pas celui de la Californie. **C'est un arbitrage qui vous
revient, et il gagnerait à être posé à un conseil.**

---

## E. COMMON CRAWL — je me suis trompé, et je le corrige

Dans le plan de l'étape 8, j'avais écrit que Common Crawl était une « piste
sous-estimée ». **C'est faux, et voici pourquoi.**

> **L'API d'index CDX exige un paramètre `url`.** Elle répond à « quelles
> captures existent pour cette adresse ou ce domaine ? » — **pas** à « quelles
> pages parlent de sous-traitance transport en Belgique ? ».
> **RAPPORTÉ — À VÉRIFIER**, l'hôte étant bloqué.

| | |
|---|---|
| Index accessible | ✅ licence ouverte |
| **Recherche par mot-clé** | 🔴 **NON** — recherche par URL/domaine uniquement |
| Recherche par contenu | ⚠️ exigerait de traiter l'index Parquet ou les WARC — **des téraoctets**, hors de portée |
| Temps réel | 🔴 **NON** — c'est une **archive**, pas un moteur |
| Notre environnement | 🔴 **000 mesuré** |
| Verdict | 🔴 **NON ADAPTÉ À LA DÉCOUVERTE** |

**Où il resterait utile** : énumérer les pages d'un domaine **déjà connu** —
c'est-à-dire la **surveillance** (circuit A), pas la découverte. Un complément
à `liens.selectionner`, jamais un moteur.

**Distinction à graver** : `INDEX / ARCHIVE ≠ MOTEUR DE RECHERCHE TEMPS RÉEL`.

---

## F. L'ARCHITECTURE MULTI-MOTEURS — déjà en place

| Garantie | État |
|---|---|
| plusieurs moteurs simultanés | ✅ `Registre(moteurs)`, ordre d'essai sans pondération |
| aucun moteur dans le cœur | ✅ 0 occurrence de `google`/`brave` dans `score`, `classification`, `pertinence`, `liens`, `recoupement` |
| chaque moteur remplaçable | ✅ contrat `MoteurRecherche` — `disponible` · `motif_indisponibilite` · `rechercher` · `mode` |
| moteur · requête · rang · URL · date · provenance | ✅ table `trouvailles`, 8a |
| un moteur absent n'arrête rien | ✅ `NON MESURÉ`, jamais `0` — prouvé en 8d |

**Rien à construire ici.** 8e est un problème d'accès et de droit, pas
d'architecture. C'était l'objet de l'étape 7 et il est réglé.

---

## G. TABLEAU D'ARBITRAGE

| Solution | Web large | Accès actuel | Notre env. | Stockage | Coût | Rappel | Adapt. | Verdict |
|---|---|---|---|---|---|---|---|---|
| Google Custom Search | ⚠️ | 🔴 fermé **(403 mesuré)** | ✅ | — | — | ✅ | ✅ | 🔴 **NON DISPONIBLE** |
| Google PSE | 🔴 50 domaines | ✅ | ✅ | ✅ | faible | 🔴 | 🔴 | 🔴 **NON ADAPTÉ** |
| Google Web Search Service | ❓ | 🔵 partenariat | ❓ | ❓ | **NON PUBLIÉ** | ❓ | ❓ | 🔵 **À DEMANDER** |
| Google Grounding | ✅ | ✅ **(400 clé, mesuré)** | ✅ | 🔴 **interdit (lu)** | 14 $/1 000 | ✅ | 🔴 | 🔴 **NON AUTORISÉ** |
| **Brave** | ✅ propre | ✅ | 🔴 **000 mesuré** | ⚠️ plan requis | ~5 $/1 000 | ✅ | ✅ **connecteur écrit** | 🟠 **SOUS CONDITIONS** |
| Exa | ✅ | ✅ | 🔴 **000** | 🔴 si confirmé | ~7 $/1 000 | ✅ | ✅ | 🔴 **NON AUTORISÉ ?** |
| Tavily | ✅ | ✅ | 🔴 **000** | ❓ | ~8 $/1 000 | ✅ | ✅ | 🟠 **SOUS CONDITIONS** |
| SerpAPI / Serper | ✅ | ✅ | 🔴 **000** | ❓ | ~25 $/1 000 | ✅ | ✅ | ⚠️ **À ARBITRER** |
| Mojeek | ✅ propre | ✅ | 🔴 **000** | ❓ | ❓ | ⚠️ | ✅ | 🔵 **À TESTER** |
| Common Crawl | 🔴 **URL only** | ✅ | 🔴 **000** | ✅ | gratuit | 🔴 | 🔴 | 🔴 **NON ADAPTÉ** |

---

## H. CE QUE LE RADAR DOIT DÉCOUVRIR — et qui écarte la moitié du tableau

Vous ne construisez pas un radar TED. Le moteur doit atteindre :
besoins privés · sous-traitance · partenariats · transporteurs et prestataires
recherchés · recrutements révélateurs · ouvertures de dépôts · expansions ·
nouveaux contrats · signaux · pages « devenir partenaire » · opportunités
locales · métiers à construire · titulaires · opportunités cachées.

**Ce que cela impose au moteur :**

| Exigence | Écarte |
|---|---|
| indexer le **web ouvert**, pas un catalogue | Google PSE, Agent Search |
| chercher par **contenu**, pas par URL | **Common Crawl** |
| rendre des **liens exploitables** | Grounding Google et Bing (texte généré) |
| couvrir **fr / nl / de** et la Belgique locale | à vérifier pour Mojeek |
| autoriser un **historique de découvertes** | Grounding Google, Exa si confirmé |

Il ne reste, en théorie : **Brave, Tavily, Mojeek**, et sous arbitrage
**SerpAPI/Serper**. **Tous bloqués par l'egress.**

---

## I. SOLUTION RECOMMANDÉE

**Aucune solution n'est démontrée.** Je ne recommande donc aucun moteur — le
recommander supposerait une preuve que je n'ai pas.

Ce que je recommande, c'est **un ordre de levée des obstacles** :

| | Action | Qui | Débloque |
|---|---|---|---|
| **1** | Ouvrir l'egress vers **un** hôte de test | vous / l'hébergeur | la seule chose qui transforme « bloqué » en « mesurable » |
| **2** | Lire les conditions de **cet** éditeur à la source | vous, ou moi une fois l'egress ouvert | le droit de conserver l'historique |
| **3** | Trancher la posture P1 / P2 / P3 sur le stockage | **vous** | la nature même de `trouvailles` |
| **4** | Souscrire le plan minimal et mesurer sur ~100 requêtes | vous | le rappel réel |
| **5** | Décider au vu des chiffres | vous | — |

**Brave reste mon candidat de tête** — index propre, connecteur écrit, plan de
stockage apparemment achetable — mais **c'est un `CANDIDAT TECHNIQUE`, pas un
choix**, et il le restera tant que les points 1 et 2 ne sont pas faits.

---

## J. SOLUTION DE REPLI

**Elle existe déjà et elle tourne.** C'est l'étape 7 :

```
entreprise connue → page surveillée → collecte directe → qualification
→ opportunité → suivi
```

Sans aucun moteur. Le radar n'est pas suspendu à 8e — il est **privé de
découverte**, ce qui n'est pas la même chose. Les sources directes (TED, BDA,
e-Procurement, BCE) sont elles aussi bloquées par l'egress : **le même geste
les débloquerait toutes.**

---

## K. CE QUI RESTE NON MESURÉ

- **La découverte web réelle, entièrement.** Aucun moteur n'a jamais tourné.
- **Le rappel réel** de n'importe quel moteur sur nos 2 203 requêtes.
- **Les conditions d'utilisation** de Brave, Exa, Tavily, SerpAPI, Serper,
  Mojeek, Common Crawl — **non lues à la source**.
- **Le coût réel** — les tarifs cités viennent de tiers, sauf Google.
- **La couverture Belgique / fr-nl-de** de chaque index.
- **Le comportement de Common Crawl** — hôte bloqué, API non essayée.

`NON MESURÉ ≠ 0`. Un moteur bloqué n'a **pas** rendu zéro résultat.

---

## L. FICHIERS QUI SERAIENT MODIFIÉS EN 8f

**Si et seulement si** un moteur devient accessible et autorisé :

| Fichier | Nature |
|---|---|
| `radar/moteurs_recherche.py` | un connecteur de plus, sur le contrat existant |
| `radar/cli.py` | l'exécution de la boucle réelle |
| `fixtures/` | un jeu d'essai figé à partir des premiers résultats réels |
| `validation/mesures/` | la mesure de rappel réelle |
| **aucun autre** | le cœur, le score, les catégories, la déduplication et les huit gelés **ne bougeront pas** |

Si la posture **P2** est retenue, s'y ajouterait `radar/trouvailles.py` — pour
**cesser de conserver** titre et extrait. Ce serait un retrait, pas un ajout.

---

## M. CE QUE JE NE FERAI PAS SANS VOUS

- signer ou recommander un contrat sur des conditions que je n'ai pas lues ;
- trancher SerpAPI / Serper à votre place ;
- décider entre P1, P2 et P3 ;
- écrire un connecteur que je ne peux ni exécuter ni mesurer ;
- présenter un moteur bloqué comme ayant rendu zéro résultat.
