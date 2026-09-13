# MATRICE DES SOURCES — recentrée sur la Belgique

État : **2026-09-13**. Aucun code. Aucun collecteur. Le moteur n'est pas touché.

---

## AVERTISSEMENT DE LECTURE — quatre états, jamais confondus

```
SOURCE IDENTIFIÉE   je sais qu'elle existe et ce qu'elle publie
SOURCE ACCESSIBLE   une requête réelle a reçu une réponse réelle
SOURCE COLLECTÉE    le radar a reçu et conservé des données d'elle
FAMILLE MESURÉE     ces données ont traversé la chaîne et produit un verdict
```

**Toutes les sources de ce document sont au premier état : IDENTIFIÉES.**
Aucune n'est accessible, aucune n'est collectée, aucune famille ne devient
mesurée grâce à ce document.

### Ce que j'ai réellement vérifié, et ce que je n'ai pas pu vérifier

| colonne | vérifiée ? | par quoi |
|---|---|---|
| l'hôte existe | ✅ **OUI** | résolution DNS réelle, IP relevée |
| accessibilité depuis l'environnement | ✅ **OUI** | requête HTTPS réelle |
| URL exacte / chemin | ❌ **NON** | de mémoire — le chemin n'a pas pu être ouvert |
| format (API / HTML / RSS / PDF) | ❌ **NON** | de mémoire — aucune réponse observée |
| robots.txt / CGU | ❌ **NON** | refusés par le gateway avant le serveur |
| accès requis (compte, abonnement) | ❌ **NON** | de mémoire |
| intérêt commercial | ⚠️ **JUGEMENT** | raisonnement, pas mesure |

Les colonnes « format », « accès requis » et « CGU » sont donc des
**hypothèses de travail à vérifier**, jamais des faits mesurés.

### Résultat d'accès — identique pour les 38 hôtes testés

```
38 hôtes testés · 38 résolus par DNS · 0 ayant répondu
tous : HTTP 403 · x-deny-reason: host_not_allowed
témoin : pypi.org → 200 · 251 417 octets, même commande
```

---

## 🟢 PRIORITÉ 1 — BELGIQUE, FORTE VALEUR COMMERCIALE

| # | source | région | famille | type d'info | pub/privé | hôte (DNS vérifié) | accès supposé | format supposé |
|---|---|---|---|---|---|---|---|---|
| 1 | **e-Notification / Bulletin des Adjudications** | fédérale | **D + E** | avis de marché ET avis d'attribution | public | `enot.publicprocurement.be` · 62.192.67.166 | libre, compte pour déposer | HTML + flux/API |
| 2 | **e-Procurement (portail)** | fédérale | D + E | procédures, documents | public | `www.publicprocurement.be` · 85.91.189.188 | libre en consultation | HTML |
| 3 | **Marchés publics de Wallonie** | Wallonie | D + E | avis régionaux | public | `marchespublics.wallonie.be` · 157.164.155.179 | libre | HTML |
| 4 | **Flows** — presse logistique belge | nationale | **F + A** | ouvertures de hubs, contrats, investissements | privé | `www.flows.be` · 2606:4700:3034::ac43:b4f7 | libre, paywall partiel | HTML + RSS |
| 5 | **Port of Antwerp-Bruges** | Flandre | **F + D + A** | concessions, terminaux, volumes, appels | public | `www.portofantwerpbruges.com` · 104.18.19.136 | libre | HTML + presse |
| 6 | **Liège Airport** | Wallonie | **F + A** | hub cargo, extensions, opérateurs | privé/public | `www.liegeairport.com` · 34.120.76.127 | libre | HTML + presse |
| 7 | **OTM** — conseil des chargeurs belges | nationale | **A + H** | **les donneurs d'ordre eux-mêmes** | privé | `www.otmbe.org` · 2a00:1c98:… | membres | HTML |
| 8 | **Febetra / TLV / UPTR** — fédérations transport | nationale | **H + F** | sous-traitance, capacité, marché | privé | `www.febetra.be` 78.47.8.218 · `www.tlv.be` · `www.uptr.be` | libre + membres | HTML |
| 9 | **Moniteur belge** | fédérale | **F + E** | constitutions, fusions, faillites, marchés | public | `www.ejustice.just.fgov.be` · 193.191.241.68 | **libre, réutilisation autorisée** | HTML + PDF |
| 10 | **BCE / KBO** — registre des entreprises | fédérale | **F + A** | création, NACE transport, sièges | public | `kbopub.economie.fgov.be` · 2001:6a8:… | libre, open data | HTML + open data |

## 🟡 PRIORITÉ 2 — BELGIQUE, VALEUR SECONDAIRE

| source | région | famille | pourquoi secondaire | hôte |
|---|---|---|---|---|
| Port de Bruxelles | Bruxelles | F + D | plus petit que Anvers, mais distribution urbaine | `port.brussels` · 5.135.140.122 |
| STIB-MIVB | Bruxelles | D | marchés de transport, rarement sous-traitance routière | `www.stib-mivb.be` · 195.244.180.240 |
| North Sea Port (Gand) | Flandre | F + D | 3ᵉ port belge, flux vracs et conteneurs | `www.northseaport.com` · 13.51.62.86 |
| Port autonome de Liège | Wallonie | F + D | trimodal, intéressant pour le second cercle | `www.portdeliege.be` · 2606:4700:20::… |
| IDELUX · IGRETEC | Wallonie | D + F | intercommunales — zonings, marchés locaux | `www.idelux.be` · `www.igretec.com` |
| citydev.brussels | Bruxelles | F | terrains et bâtiments logistiques | `citydev.brussels` · 174.129.25.170 |
| hub.brussels · AWEX · FIT | 3 régions | F | implantations d'entreprises étrangères | `hub.brussels` · `www.awex.be` · `www.flandersinvestmentandtrade.com` |
| VIL — institut flamand logistique | Flandre | F | projets, études, consortiums | `www.vil.be` · 78.47.8.218 |
| Comptes annuels — Banque nationale | fédérale | F | santé financière d'un prospect | `consult.cbso.nbb.be` · 150.171.110.210 |
| Statbel · data.gov.be · SPF Mobilité | fédérale | F | volumes et flux, contexte plus que signal | `statbel.fgov.be` · `data.gov.be` · `mobilit.belgium.be` |
| VDAB · Forem · Actiris | 3 régions | **F** | **recrutement massif de chauffeurs = signal** | `www.vdab.be` · `www.forem.be` · `www.actiris.be` |
| Voka · BECI · UCM | 3 régions | F + A | chambres — annonces d'implantation | `www.voka.be` · `www.beci.be` · `www.ucm.be` |
| L'Echo · De Tijd · Trends · Bruzz | nationale | F | presse économique, paywall probable | `www.lecho.be` · `trends.knack.be` · `www.bruzz.be` |
| TransportMedia | nationale | F | presse transport, complément de Flows | `www.transportmedia.be` · 78.46.10.148 |
| be.brussels · wallonie.be · vlaanderen.be | 3 régions | D + F | portails régionaux, dispersés | tous résolus, tous 403 |

## 🔵 PRIORITÉ 3 — BENELUX (second cercle)

| source | pays | famille | intérêt pour un transporteur belge | hôte |
|---|---|---|---|---|
| **TenderNed** | NL | D + E | marchés néerlandais — flux Rotterdam→Belgique | `www.tenderned.nl` · 2a04:9a00:… |
| Port of Rotterdam | NL | F | premier port d'Europe, alimente nos flux | `www.portofrotterdam.com` · 2a06:98c1:… |
| PIANOo | NL | D | centre d'expertise achats publics NL | `www.pianoo.nl` · 2001:4c10:… |
| Portail marchés publics | LU | D + E | Luxembourg, proximité Arlon/Luxembourg | `pmp.b2g.etat.lu` · 185.106.24.206 |

## ⚪ PRIORITÉ 4 — FRANCE / UE — **conservées, déclassées**

Ces sources **gardent une vraie valeur** et ne sont pas supprimées. Elles
cessent simplement d'être le cœur du radar.

| source | famille | valeur réelle pour nous | hôte |
|---|---|---|---|
| **TED** — Tenders Electronic Daily | **D + E** | **couvre la Belgique** : tout marché belge au-dessus des seuils européens y paraît. Un collecteur existe déjà (`collecter_ted.py`). C'est la source UE la plus utile — et elle est belge autant qu'européenne. | `api.ted.europa.eu` |
| data.europa.eu | D + E | portail open data UE, agrège TED | `data.europa.eu` |
| BOAMP | D + E | France seule — utile pour les flux nord de la France | `www.boamp.fr` |
| data.gouv.fr · marches-publics.gouv.fr | D | France, valeur indirecte | résolus, 403 |
| Contracts Finder (UK) | D + E | hors UE, flux marginaux | `contractsfinder.service.gov.uk` |

## 🔴 À ÉCARTER

| source | pourquoi |
|---|---|
| **Bourses de fret** — Teleroute, TimoCom, Trans.eu, Wtransnet, Transporeon | **deux murs** : compte payant ET collecte automatisée interdite par les CGU. Écartées tant qu'un accès contractuel n'est pas fourni. Ce n'est pas un problème technique. |
| Agrégateurs d'emploi — Indeed, Jooble | mesurés le 2026-09-12 : produisent des ⚪ HYPOTHÈSE sans demandeur nommé. Bruit. |
| Annuaires — Europages | listent des transporteurs, pas des besoins. Mauvais côté du marché. |
| Presse généraliste sans angle économique | signal trop dilué pour le coût de lecture. |

---

## COUVERTURE A–H PAR LES SOURCES IDENTIFIÉES

| famille | sources belges identifiées | la meilleure | état |
|---|---|---|---|
| **A** entreprise exprimant un besoin | pages « devenir partenaire », OTM, chambres | OTM — les chargeurs eux-mêmes | **MESURÉE** (2 pages) |
| **B** bourse de fret | Teleroute, TimoCom, Trans.eu… | — | **NON MESURÉE — écartée** (2 murs) |
| **C** moteur de recherche | — | — | **MESURÉE** |
| **D** marchés publics | e-Notification, Wallonie, TED | e-Notification | **MESURÉE** (1 donnée) |
| **E** attribution | e-Notification, TED, Moniteur belge | **TED — collecteur déjà écrit** | **NON MESURÉE** |
| **F** signal économique | Flows, ports, Moniteur, BCE, VDAB | Flows + Moniteur belge | **NON MESURÉE** |
| **G** renouvellement | déduit des attributions (E) + calendrier interne | **dépend de E** | **NON MESURÉE** |
| **H** partenariat / sous-traitance | Febetra, TLV, UPTR, OTM | fédérations professionnelles | **NON MESURÉE** |

**G ne demande aucune source nouvelle** : le radar calcule déjà les remises en
concurrence à partir des attributions (`radar.cli calendrier`). Mesurer **E**
ouvre **G** par construction. C'est le meilleur rapport effort/couverture du
plan : **une source, deux familles.**

---

## ADÉQUATION AU MODÈLE « EUROPE → BELGIQUE → DÉPÔT → DISTRIBUTION BELGE »

| maillon | ce qu'il faut détecter | sources les plus utiles |
|---|---|---|
| **Europe → Belgique** | flux entrants, volumes, nouveaux opérateurs | Port of Antwerp-Bruges · North Sea Port · Port of Rotterdam · Liège Airport |
| **Arrivée / dépôt** | ouvertures d'entrepôts, concessions, zonings | Flows · citydev.brussels · IDELUX/IGRETEC · VIL |
| **Distribution belge** | besoins de sous-traitance, tournées, derniers km | **OTM · Febetra/TLV/UPTR** · pages « devenir partenaire » · e-Notification |
| **Transversal** | qui bouge, qui grandit, qui recrute | Moniteur belge · BCE/KBO · VDAB/Forem/Actiris · comptes annuels NBB |

Le maillon le moins couvert est le troisième — **la distribution belge**, qui
est justement notre métier. Les deux sources qui l'adressent directement
(**OTM**, **fédérations**) sont aussi les seules de la priorité 1 dont l'accès
libre n'est pas certain : elles sont réservées aux membres. **C'est une
adhésion professionnelle, pas un réglage réseau.**

---

## LES 10 SOURCES BELGES À DÉBLOQUER EN PRIORITÉ

Classées par **opportunité commerciale concrète attendue**, pas par facilité.

**1. TED — `api.ted.europa.eu`** · familles **D + E + (G)**
Tous les marchés belges au-dessus des seuils européens y paraissent, avis
d'attribution compris. `outils/collecter_ted.py` est **déjà écrit** et vise
l'API en `scope ALL` avec 9 familles CPV transport. *Opportunité concrète* :
un marché de distribution ouvert que nous pouvons déposer ; et chaque
attribution alimente le calendrier de remise en concurrence — **une source,
trois familles**. C'est le meilleur premier coup, et le moins cher.

**2. e-Notification — `enot.publicprocurement.be`** · **D + E**
Le Bulletin des Adjudications belge. Contient ce que TED ne contient pas :
les marchés **sous les seuils européens** — communes, intercommunales, CPAS,
hôpitaux. *Opportunité concrète* : c'est là que se trouvent les marchés de
taille PME, ceux qu'une entreprise de notre gabarit peut réellement gagner.

**3. Flows — `www.flows.be`** · **F + A**
La presse logistique belge de référence. *Opportunité concrète* : « X ouvre
un entrepôt de 20 000 m² à Willebroek » est un besoin de transport
**avant** qu'il devienne un appel d'offres. C'est exactement la promesse du
radar : arriver avant que tout le monde ait vu.

**4. Moniteur belge — `www.ejustice.just.fgov.be`** · **F + E**
Publications légales obligatoires : constitutions, fusions, transferts de
siège, faillites. Gratuit, réutilisation autorisée. *Opportunité concrète* :
une faillite de transporteur libère ses clients — ce sont des prospects
immédiats, avec une urgence réelle et une concurrence encore inexistante.

**5. Port of Antwerp-Bruges — `www.portofantwerpbruges.com`** · **F + D + A**
Le premier maillon de notre modèle. Concessions, nouveaux terminaux,
opérateurs qui s'installent, appels d'offres du port. *Opportunité concrète* :
un nouvel opérateur logistique à Anvers a besoin de post-acheminement vers la
Belgique — notre métier exact.

**6. OTM — `www.otmbe.org`** · **A + H**
Le conseil des **chargeurs** belges : les donneurs d'ordre eux-mêmes, pas les
transporteurs. *Opportunité concrète* : la source la plus proche de l'argent.
Réserve — l'accès est probablement réservé aux membres ; ce serait une
adhésion à payer, pas un hôte à ouvrir.

**7. Marchés publics de Wallonie — `marchespublics.wallonie.be`** · **D + E**
Le versant régional wallon, avec les pouvoirs locaux. *Opportunité
concrète* : marchés de transport scolaire, collecte, navettes — récurrents,
pluriannuels, à notre échelle.

**8. BCE / KBO — `kbopub.economie.fgov.be`** · **F + A**
Registre des entreprises, open data. *Opportunité concrète* : filtrer les
créations et changements d'adresse sur les codes NACE transport et entrepôt
donne une liste de prospects **avant** toute communication publique.

**9. Febetra / TLV / UPTR — `www.febetra.be`, `www.tlv.be`, `www.uptr.be`** · **H + F**
Les fédérations professionnelles. *Opportunité concrète* : la sous-traitance
entre transporteurs est un marché réel et invisible des portails publics —
c'est la seule voie identifiée vers la famille H depuis une source belge.

**10. Liège Airport — `www.liegeairport.com`** · **F + A**
Premier hub cargo belge et 5ᵉ européen. *Opportunité concrète* : chaque
nouvel opérateur ou extension d'entrepôt y crée un besoin de distribution
routière vers toute la Belgique.

---

## CE QUI DÉPEND MAINTENANT D'UN RÉGLAGE RÉSEAU

**8 des 10** ne demandent que l'ouverture de leur hôte dans les réglages
d'egress de l'environnement. Ce sont des sources **publiques et gratuites**.

**2 sur 10** — OTM et les fédérations — demandent en plus une **adhésion
professionnelle**. Ce n'est pas technique.

Si un seul hôte devait être ouvert : **`api.ted.europa.eu`**. Le collecteur
existe, il couvre D et E, il ouvre G par construction, et il fournirait enfin
les avis d'attribution réels dont P1-B a besoin pour être tranché.

Aucune de ces sources n'est mesurée. Ce document ne change aucun compteur :
**7 données réelles, 3 familles sur 8.**
