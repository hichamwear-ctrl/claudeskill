# AUDIT DES MOTEURS DE RECHERCHE WEB DU RADAR COMMERCIAL

Date : 2026-09-13 · Aucun code modifié · Mesures brutes : `validation/acces/2026-09-13-moteurs-recherche.json`

## Convention de lecture — quatre niveaux, jamais mélangés

| Niveau | Question | Qui répond |
|---|---|---|
| **A. PRODUIT EXISTE** | Le produit existe-t-il aujourd'hui ? | annuaire public, page produit de l'éditeur |
| **B. ACCÈS AUTORISÉ** | Avons-nous le droit contractuel de l'utiliser *pour un radar* ? | conditions officielles lues |
| **C. ACCÈS TECHNIQUE** | Notre environnement peut-il l'atteindre ? | `curl` depuis CE conteneur |
| **D. TEST RÉEL** | Une requête a-t-elle réellement rendu des résultats ? | mesure |

`HTTP=000` = tunnel CONNECT refusé par la passerelle d'egress (403, `text/plain`).
Ce n'est **pas** une panne DNS — le DNS résout. Ce n'est **pas** une indisponibilité du produit.

---

## 1. GOOGLE

Google n'a pas « une » API de recherche. Il en a quatre voies distinctes, de statuts opposés.

### 1.1 Custom Search JSON API

| | |
|---|---|
| Produit | **EXISTE** — `customsearch v1`, `preferred: true`, révision 20260910 |
| Accès autorisé | **FERMÉ AUX NOUVEAUX CLIENTS** |
| API | REST, clé simple + `cx` |
| Recherche Web large | oui pour les moteurs historiques ; **non** pour les nouveaux (voir 1.2) |
| Coût | 100 req/j gratuites puis 5 $ / 1 000, plafond 10 000/j |
| Éligibilité | ❌ |
| État réel | `customsearch.googleapis.com` **JOIGNABLE** |
| **Test réel** | **FAIT** — `403 PERMISSION_DENIED` : « This project does not have the access to Custom Search JSON API. » avec la clé et le `cx` du projet de l'exploitant |
| **Verdict** | 🔴 **FERMÉ — mesuré, pas supposé** |

> Sécurité : la clé utilisée pour ce test est **COMPROMISE** et doit être révoquée. Elle n'apparaît nulle part dans le dépôt.

### 1.2 Programmable Search Engine

Les nouveaux moteurs sont limités à 50 domaines ; « Search the entire web » a été retiré à la création (annonce de fin janvier 2026) ; les moteurs full-web existants doivent migrer avant le 2027-01-01. **Un PSE créé aujourd'hui ne peut pas fouiller le web belge.**

### 1.3 Web Search Service API (`websearchservice.googleapis.com`)

| | |
|---|---|
| Produit | **NON CONFIRMÉ** — absent de l'annuaire des **530** API Google (revérifié ce jour) ; document de découverte **404** ; toutes les variantes de chemin rendent du **HTML 404**, là où une vraie API publique Google rend du **JSON 400** avec une clé bidon |
| Accès autorisé | **RÉSERVÉ** — exige `clientContext.clientId`, un « designated partner client ID » lié à un accord de partenariat |
| Coût / Quota | **NON PUBLIÉ** |
| État réel | **NON MESURABLE** — aucun chemin d'API valide |
| **Verdict** | 🔵 **VOIE PARTENAIRE — à demander, pas à intégrer** |

### 1.4 Grounding with Google Search — le cas le plus important de tout l'audit

| | |
|---|---|
| Produit | **EXISTE**, facturé, tarif public |
| Coût **vérifié ce jour sur la page Google** | Gemini 3 : **5 000 Grounding Queries/mois sans frais**, puis **14 $ / 1 000**. Gemini 2.5 Flash / 2.0 Flash : 1 500 prompts/jour gratuits. Gemini 2.5 Pro : 10 000/jour. Au-delà : 35 $ / 1 000. Facturation démarrée le 2026-01-05. |
| **Accès technique** | ✅ **ÉTABLI** — seul moteur de recherche au monde joignable depuis ce conteneur |
| **Accès autorisé** | 🔴 **INTERDIT POUR NOTRE USAGE** |

Test technique réellement effectué :

```
POST generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
   tools: [{"google_search": {}}]        → HTTP 400 · API_KEY_INVALID
```

Le service a été atteint **au niveau du chemin**, pas seulement de l'hôte. Il ne manque qu'une clé valide.
*Honnêteté :* le rejet portant sur la clé arrive **avant** la validation de l'outil — on ne peut donc pas conclure que `google_search` fonctionnerait.

Mais la clause 20(k)(i)(2) des *Service Specific Terms* Google Cloud, lue ce jour, dit :

> « […] it is a violation of these terms to use Grounding with Google Search to extract or collect one or more of these components for another purpose (for example, **using programmatic or automated means to collect Links, using Links to build an index, or using Links to identify destination pages for crawling or scraping**). »
> « Customer does not allow Grounded Results to be: (i) accessed or collected by automated or programmatic means, or (ii) **to be used to create a database**. »

Le radar collecte des liens par moyen programmatique, construit un index, en fait une base de données, et s'en sert pour identifier des pages à récupérer. **C'est mot pour mot ce que la clause interdit.** Le seul moteur joignable est donc juridiquement inéligible. La clause 20(l) étend la même interdiction à *Web Grounding for Enterprise*.

Par ailleurs `vertexaisearch.cloud.google.com` — l'hôte des URL de redirection que rend le grounding — est **bloqué** par la passerelle : même autorisé, les liens rendus seraient inexploitables ici.

### 1.5 Agent Search (ex-Vertex AI Search)

C'est la voie de repli que Google indique aux clients de Custom Search. Elle ne répond pas au besoin :

> Clause 21 : « Customer may use only Customer Data and **web domains that it owns or is authorized to utilize**. »

Ce n'est pas un moteur web généraliste, c'est un moteur sur **nos** données et **nos** domaines. 🔴 **HORS SUJET.**

### 1.6 Toutes les autres API Google

`cloudsearch` (Workspace) · `doubleclicksearch`/`searchads360` (publicité) · `indexing` (soumettre ses propres URL) · `kgsearch` (Knowledge Graph) · `retail` (catalogue e-commerce) · `searchconsole` (son propre site).
**Aucune ne fait de recherche web programmatique généraliste.**

### VERDICT GOOGLE

🟠 **GOOGLE EN ATTENTE D'ACCÈS.** Le produit historique est fermé ; le seul chemin techniquement ouvert est contractuellement interdit pour un radar ; la voie utilisable est une voie partenaire à demander.

---

## 2. BING

### 2.1 Bing Search API v7 — le produit que l'architecture supposait

| | |
|---|---|
| Produit | 🔴 **RETIRÉ le 2025-08-11** — Web, Custom, News, Image, Video, Entity. Instances existantes décommissionnées. **Aucune nouvelle clé ne peut être obtenue.** |
| Accès autorisé | sans objet |
| Accès technique | sans objet |
| Test réel | impossible |

### 2.2 Grounding with Bing Search — le remplaçant officiel

| | |
|---|---|
| Produit | **EXISTE** — dans Azure AI Foundry / Foundry Agent Service |
| Coût | **14 $ / 1 000 transactions**, plafonds 150/s et 1 000 000/jour, **pas de palier gratuit annoncé** |
| Recherche Web large | ❌ **non** — rend du texte généré cité, pas une liste de résultats |
| Accès autorisé | 🔴 **INADAPTÉ** — page officielle Microsoft : « designed to function as an add-on feature for select Microsoft products », « **Outputs are not directly accessible for use in other applications or programs** », citations obligatoires |
| Accès technique | 🔴 **BLOQUÉ** — `api.bing.microsoft.com` (403 CONNECT), `management.azure.com`, `*.api.cognitive.microsoft.com`, `ai.azure.com`, `learn.microsoft.com` : tous refusés. Seuls `portal.azure.com` (403 Azure Front Door) et `login.microsoftonline.com` (302 authentique) répondent — inutiles pour appeler une API. |
| Test réel | ❌ **JAMAIS TESTÉ** |

### VERDICT BING

🔴 **BING — ACCÈS BLOQUÉ**, et sur **trois niveaux simultanés** : le produit demandé n'existe plus (A), son remplaçant est contractuellement inadapté à un radar (B), et son hôte est injoignable depuis notre environnement (C).

**Conséquence d'architecture : Bing ne peut pas être la PRIORITÉ 2.** Ce n'est pas un arbitrage, c'est un constat. La place de priorité 2 est vacante et doit être réattribuée.

---

## 3. AUTRES MOTEURS

| Moteur | A. Produit | B. Autorisé | C. Technique | D. Testé | Coût | Classe |
|---|---|---|---|---|---|---|
| **Brave Search API** | ✅ index propre indépendant | ⚠️ **plan avec droits de stockage requis** — les conditions standard interdisent de stocker/mettre en cache/constituer une base | 🔴 bloqué | ❌ | ~4-5 $ / 1 000 · palier gratuit supprimé en février 2026 | 🟢 **PRIORITAIRE** |
| **Exa** | ✅ recherche sémantique | ❓ **À VÉRIFIER** — conditions de stockage non lues à la source | 🔴 bloqué | ❌ | ~7 $ / 1 000 · ~20 000 req/mois gratuites | 🟡 **COMPLÉMENTAIRE** |
| **Tavily** | ✅ | ❓ **À VÉRIFIER** | 🔴 bloqué | ❌ | ~7,50-8 $ / 1 000 · 1 000 crédits/mois | 🟡 **COMPLÉMENTAIRE** |
| **SerpAPI** | ✅ | ⚠️ **zone grise** — revend l'accès aux résultats d'un moteur tiers ; la conformité repose sur l'éditeur, pas sur nous | 🔴 bloqué | ❌ | 25 $ / 1 000 · 250/mois gratuites | 🔵 **À TESTER après arbitrage juridique** |
| **Serper** | ✅ | ⚠️ même zone grise | 🔴 bloqué | ❌ | — | 🔵 **À TESTER** |
| **DuckDuckGo** | ❌ pas d'API de résultats web | — | 🔴 bloqué | ❌ | — | 🔴 **NON ADAPTÉ** |

**Brave est classé prioritaire** parce qu'il cumule trois propriétés qu'aucun autre n'a ensemble : index **propre et indépendant** (donc recall réellement différent de Google), plan **explicitement autorisant le stockage** (donc compatible avec une base d'opportunités), et **connecteur déjà écrit** dans `radar/moteurs_recherche.py`.

---

## 4. TABLEAU COMPARATIF

| Critère | Google CSE | Google Grounding | Google Partner API | Bing v7 | Bing Grounding | Brave | Exa | Tavily | SerpAPI |
|---|---|---|---|---|---|---|---|---|---|
| Recherche Web large | ⚠️ historiques seulement | ✅ | ✅ présumé | ✅ | ❌ texte généré | ✅ | ✅ | ✅ | ✅ |
| API programmatique | ✅ | ✅ | ✅ | ✅ | ⚠️ agent | ✅ | ✅ | ✅ | ✅ |
| Usage PME commerciale | ❌ fermé | ❌ interdit | ❓ partenariat | ❌ retiré | ❌ add-on | ✅ plan payant | ✅ | ✅ | ⚠️ |
| Coût / 1 000 | 5 $ | 14 $ | NON PUBLIÉ | — | 14 $ | 4-5 $ | 7 $ | 7,5-8 $ | 25 $ |
| Palier gratuit | 100/j | 5 000/mois | NON PUBLIÉ | — | aucun | supprimé | ~20 000/mois | 1 000/mois | 250/mois |
| Couverture Belgique | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| FR / NL / DE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| Automatisable | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **État réel ici** | 🔴 403 mesuré | 🟠 joignable / interdit | 🔵 à demander | 🔴 n'existe plus | 🔴 bloqué | 🔴 egress | 🔴 egress | 🔴 egress | 🔴 egress |

---

## 5. ARCHITECTURE RECOMMANDÉE

L'architecture ne change pas parce que Google est fermé. Elle est **confirmée** par le fait que Google est fermé : un radar qui aurait été construit autour de Google serait aujourd'hui à l'arrêt total.

### 5.1 Principe fondateur

> **Google est le moteur de découverte PRIORITAIRE, mais le radar est conçu pour exploiter plusieurs moteurs afin d'augmenter le recall et d'éviter une dépendance technique unique.**

Et la règle absolue, déjà en vigueur et non négociable :

> **SOURCE ≠ QUALITÉ.** La source sert à la provenance, à la traçabilité, à l'analyse de performance des capteurs, à la déduplication et au diagnostic. **Jamais au score commercial.** Interdit : `Google = +20`, `Bing = +10`, `TED = +30`.

Une opportunité trouvée par Tavily et une opportunité trouvée par Google reçoivent **exactement le même score** si elles décrivent le même besoin. La provenance change ce qu'on sait de la *source*, jamais ce qu'on sait du *client*.

### 5.2 Ce qui existe déjà et qui est correct

`radar/moteurs_recherche.py` contient l'abstraction demandée :

```
MoteurRecherche : .disponible · .motif_indisponibilite · .rechercher(requete) -> list[Resultat]
Resultat        : titre · url · extrait · requete · fournisseur · consulte_le
Registre        : plusieurs moteurs, chacun avec son état
depuis_environnement(env) : lit GOOGLE_API_KEY / GOOGLE_CSE_ID / BRAVE_API_KEY
```

Aucun `if google` dans le cœur. Le cœur reçoit des `Resultat`, sans savoir qui les a produits — sauf pour les tracer.

### 5.3 Ce qu'il faut y ajouter — **sans le coder avant validation**

**a. Contrat de résultat enrichi.** Ajouter `rang` au `Resultat` (place dans la liste rendue par le moteur). Il sert au **diagnostic de capteur**, jamais au score.

**b. Fusion de provenance.** Une même page trouvée par deux moteurs = **une opportunité, deux provenances**. La provenance devient une liste, pas un champ. Trouvée deux fois ≠ meilleure : c'est une information sur les moteurs, pas sur le client.

**c. Déduplication par empreinte de besoin, pas par vocabulaire.** Deux annonces qui décrivent le même besoin avec des mots différents sont **un** doublon ; deux annonces au vocabulaire identique pour deux dépôts différents ne le sont pas.

**d. Chaîne de repli explicite.** Ordre de tentative, jamais de pondération de score. Un moteur indisponible passe la main ; il ne dégrade rien.

**e. État par source, affiché.** `JAMAIS CONSULTÉE` · `CONSULTÉE` · `ERREUR` · `NON DISPONIBLE`. Une source jamais consultée n'est **pas** une source sans résultat. `NON MESURÉE ≠ 0`.

**f. Métriques de recall.** Par moteur : uniques trouvées **par lui seul**, communes avec les autres, taux de déduplication. C'est ce qui répond à « ce moteur vaut-il son abonnement ».

**g. Priorité apprise, jamais supposée.** État initial obligatoire : **TOUTES LES SOURCES = NON MESURÉES**. Le rendement se constate. Il ne se décrète pas. `Requete.rendement()` fait déjà exactement cela pour les requêtes — le même mécanisme, appliqué aux moteurs.

### 5.4 Les sources directes ne sont pas des moteurs

TED, e-Procurement belge, BCE/KBO, bourses de fret, pages « devenir partenaire » : ce sont des **sources directes**, indépendantes de tout moteur. Elles doivent rester atteignables même si **zéro** moteur ne l'est. C'est l'application du principe déjà gelé : **aucune source ne peut être indispensable.**

Et c'est la voie qui, aujourd'hui, a le meilleur rapport effort/résultat : elle ne dépend d'aucun contrat de moteur.

---

## 6. CE QUI EST DÉJÀ VRAIMENT TESTÉ

Mesuré, reproductible, horodaté :

1. **Custom Search JSON API : 403 PERMISSION_DENIED** avec la clé et le `cx` réels de l'exploitant. Fermeture **prouvée**, pas déduite.
2. **`generativelanguage.googleapis.com` atteint au niveau du chemin** : HTTP 400 `API_KEY_INVALID`, `server: scaffolding on HTTPServer2`.
3. **Joignabilité mesurée de 21 hôtes** (voir le JSON). Joignables : `cloud.google.com` (200), `customsearch`/`discoveryengine`/`aiplatform`/`generativelanguage.googleapis.com` (404), `portal.azure.com` (403 Front Door), `login.microsoftonline.com` (302). **Tous les autres : refus de tunnel.**
4. **`api.bing.microsoft.com` : `CONNECT tunnel failed, response 403`** — signature exacte du refus de passerelle, pas d'une panne.
5. **Annuaire Google revérifié : 530 API.** `websearchservice` **absent**. `customsearch v1` présent.
6. **Tarifs Google lus sur la page de Google**, récupérée depuis ce conteneur (HTTP 200, 3 207 537 octets) — pas depuis un blog.
7. **Clauses 20(k), 20(l) et 21** lues sur `cloud.google.com/terms/service-terms` (HTTP 200, 1 018 347 octets).
8. **Honnêteté du connecteur vérifiée** : sans clé, `google NON DISPONIBLE`, `BOUCLE NON LANCÉE`, 0 opportunité, 0 résultat simulé.

## 6 bis. CE QUI VIENT DE LA DOCUMENTATION, PAS D'UN TEST

À ne pas confondre avec ce qui précède :

- Retrait des Bing Search APIs au 2025-08-11 : **annonce Microsoft**, non testable ici (`learn.microsoft.com` bloqué).
- Tarifs et paliers gratuits de Brave, Exa, Tavily, SerpAPI : **pages tierces**, non vérifiés à la source (hôtes bloqués).
- Conditions de stockage de Brave : **rapportées**, non lues sur la page officielle.
- Limitation des nouveaux PSE à 50 domaines : **annonce Google**, non testée.
- URL de redirection du grounding Google : **documentées**, non observées ici.

## 7. CE QUI EST BLOQUÉ

| Blocage | Nature | Levable par |
|---|---|---|
| Custom Search JSON API | **commercial** — fermé aux nouveaux clients | personne. Définitif. |
| Grounding with Google Search | **juridique** — clause 20(k) | Google seul, en changeant ses conditions |
| Web Search Service API | **contractuel** — accord de partenariat | demande de partenariat |
| Bing Search API v7 | **produit supprimé** | personne. Définitif. |
| Grounding with Bing | **juridique + egress** | Microsoft + liste blanche |
| Brave · Exa · Tavily · SerpAPI · Serper | **egress uniquement** | **ajout à la liste blanche du conteneur** |

**Le blocage dominant n'est pas Google. C'est l'egress.** Cinq moteurs sur six sont bloqués par **une seule cause, purement technique, et levable sans négocier avec qui que ce soit.**

## 8. CE QUI DOIT ÊTRE FAIT ENSUITE

Par ordre de rendement, pas par ordre de préférence.

1. **Révoquer la clé Google compromise.** Immédiat. Rien d'autre ne dépend de cette action.
2. **Demander l'ouverture de l'egress vers `api.search.brave.com`.** Un seul hôte. Lève d'un coup le niveau C pour le moteur le mieux classé. C'est la seule action qui transforme un blocage en test réel.
3. **Souscrire un plan Brave accordant les droits de stockage**, et lire ses conditions **à la source** avant de payer.
4. **Test réel Brave** sur un échantillon des 2 203 requêtes → première mesure de recall réelle du projet.
5. **En parallèle, sources directes** (TED, e-Procurement belge) : elles ne dépendent d'aucun moteur et restent le chemin le plus court vers une première opportunité réelle.
6. **Demander l'accès partenaire Web Search Service** — délai long, à lancer tôt, sans en dépendre.
7. **Ne rien coder** tant que l'architecture du §5.3 n'est pas validée.

---

## VERDICT

# 🔴 AUCUN MOTEUR WEB PROGRAMMATIQUE N'EST ACTUELLEMENT ACCESSIBLE

Avec la nuance qui compte, et qui n'est pas une consolation :

- **Google n'est pas « en panne ». Google est fermé par décision commerciale et par clause contractuelle.** Le seul chemin techniquement ouvert nous est interdit précisément parce que nous voulons construire une base de données — c'est-à-dire précisément parce que nous construisons un radar.
- **Bing n'est pas une priorité 2 en attente. Bing n'existe plus** sous la forme dont le projet avait besoin.
- **Les quatre moteurs indépendants ne sont bloqués que par l'egress** — un mur technique, pas un mur juridique ni commercial.

**Conclusion à retenir :** le principe *« aucune source ne peut être indispensable »* vient d'être validé par les faits. Le radar est à l'arrêt de collecte, mais il n'est pas à refaire : ses 2 203 requêtes, son abstraction multi-moteurs et son honnêteté d'affichage sont intactes et corrects. **Il manque un moteur atteignable, pas une architecture.**
