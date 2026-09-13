# PLAN DE DÉCISION — trois questions ouvertes

Date : 2026-09-13 · **Aucun code écrit** · État de référence : commit `a2061cb`, 731 tests verts

---

## Q1 — LE CURSEUR DES PAGES PROMUES

### Ce que la mesure dit, et ce n'est pas ce que je croyais

Sur les 11 pages promues à partir de la page réelle Colis Privé, **10 le sont
sur une seule et même preuve** : `domaine_transport = True`, déclenché par
**un mot générique**.

| Page promue | Mot déclencheur | Rôle détecté |
|---|---|---|
| `/reprogrammer-une-livraison/` | « livraison » | A_VERIFIER |
| `/aide/thematique/recevoir-mon-colis/` | « colis » | A_VERIFIER |
| `/aide/thematique/colis-recu/` | « colis » | A_VERIFIER |
| `colisprive.com/agence/Account/Login.aspx` | « colis » | A_VERIFIER |
| `/devenir-relais/` | « colis » | A_VERIFIER |
| `storebelux.colisprive.com/CPS/connexion` | « colis » | A_VERIFIER |
| `/devenir-partenaire-livraison/` | « livraison » | A_VERIFIER |
| `/travailler-pour-colis-prive/` | « colis » | A_VERIFIER |
| `/aide/thematique/e-commercants/` | « livraison » | A_VERIFIER |
| `www.cevalogistics.com/fr` | « colis » + famille `logistique_entrepot` | A_VERIFIER |
| `/en/become-a-delivery-partner/` | « delivery » | **PRESTATAIRE** |

### Le problème n'est PAS le seuil. Il est double.

**1. Le nom de l'entreprise est un mot du métier.**
« Colis Privé » contient « colis ». Chaque libellé de lien du site porte donc
le vocabulaire de domaine. Un espace de connexion devient « pertinent » parce
que la marque s'appelle Colis Privé. Ce défaut frapperait à l'identique
Transports Dupont, DHL Express ou Logistics Belgium — c'est-à-dire **la
majorité de nos cibles**.

**2. Ma règle promeut sur l'ABSENCE de contre-preuve.**
`FORTE = domaine reconnu ET rôle ≠ FOURNISSEUR`. Or `A_VERIFIER` signifie
« je n'ai pas pu trancher », pas « c'est une prestation ». Sur un libellé de
trois mots, le détecteur de rôle ne tranche presque jamais. **J'ai donc traité
l'incertitude comme une preuve.**

C'est exactement ce que le projet s'interdit depuis le début :

> l'absence d'un mot-clé ne doit jamais rejeter, **sa présence ne doit jamais
> promouvoir** · INCERTAIN vaut mieux qu'INCORRECT

`domaine_transport` est d'ailleurs documenté dans `radar/activite.py` comme
l'équivalent textuel d'un **CPV générique** : il confirme qu'on parle de
transport, il ne dit pas **quoi**. L'utiliser pour promouvoir lui fait porter
une décision qu'il n'a jamais été conçu pour porter.

### Ce que les variantes donnent, mesuré sur la même page

| Règle | Promues | Ce qu'elle attrape |
|---|---|---|
| **A** — actuelle : domaine **et** rôle ≠ FOURNISSEUR | **11** | tout le site, connexion comprise |
| **B** — exiger une preuve de rôle **PRESTATAIRE** | **1** | `become-a-delivery-partner` seulement |
| **C** — exiger une **famille** (spécialité), pas le domaine | **1** | `cevalogistics.com` seulement |
| **D** — famille **ou** rôle prestataire | **2** | les deux ci-dessus |

**Aucun de ces chiffres n'est « bon ».** 11 est trop bruyant, 1 et 2 ratent la
page française `/devenir-partenaire-livraison/` — qui est précisément
l'opportunité réelle du dossier.

### Pourquoi la variante B rate la page française : une asymétrie de langue

`config/roles.yaml` contient `delivery partner` (**en**) mais **pas**
`partenaire de livraison` (**fr**). Il contient `partenaire transport`,
`partenaire logistique`, `partenaire transporteur` — mais pas la formulation
française la plus courante du même métier.

Simulation faite **en mémoire, rien n'a été écrit** :

```
page Colis Privé — config actuelle          rôle = A_VERIFIER
page Colis Privé — avec « partenaire de livraison » en fr
                                            rôle = PRESTATAIRE
```

**C'est une décision métier, pas une correction technique.** `config/roles.yaml`
alimente la classification et le score : ajouter ce terme changerait le rôle de
la page de référence, donc potentiellement son score de 55. Je ne le fais pas.

### Ce qui distinguerait réellement les sept natures de page

Vous demandez : page commerciale · partenaire · recrutement · client · FAQ ·
connexion · information générale · véritable besoin de prestataire.

Le vocabulaire de domaine ne peut pas les distinguer — il est identique dans
les sept. Ce qui les distingue est **la position du lecteur** :

| Nature | Qui parle à qui | Marqueur structurel disponible |
|---|---|---|
| besoin de prestataire | l'entreprise cherche un fournisseur de transport | rôle PRESTATAIRE + formulation à la 1ʳᵉ personne |
| partenaire | idem, plus vague | chemin `devenir-…`, `become-a-…`, `worden` |
| recrutement | l'entreprise cherche un salarié | rôle + exigence de contrat de travail |
| client / FAQ | l'entreprise parle à son acheteur final | formulation à la 2ᵉ personne, `aide/`, `faq/` |
| connexion | aucune information | formulaire d'authentification, `login`, `connexion` |
| information générale | l'entreprise parle d'elle | `qui-sommes-nous`, `actualites` |

**Deux données supplémentaires existent déjà dans le projet et ne sont pas
utilisées ici :**

1. **`radar/porte.py`** — il sait déjà lire un formulaire. Un formulaire
   d'authentification (champ mot de passe) et un formulaire de candidature
   (plusieurs champs, pas de mot de passe) ne se ressemblent pas. C'est
   observable, pas supposé.
2. **`radar/portee.py` et les segments** — le vocabulaire lu dans un **menu**
   ou un **pied de page** ne caractérise pas le besoin. Le mécanisme existe et
   est appliqué aux exclusions ; il ne l'est pas à la promotion.

### Les trois options que je vous soumets

| | Option | Effet | Coût |
|---|---|---|---|
| **1** | **Rendre la promotion automatique plus exigeante** : exiger une preuve positive (famille **ou** rôle PRESTATAIRE), le reste reste CANDIDATE | 11 → 2 sur cette page · aucune fausse promotion · la page française reste candidate jusqu'à sa collecte | ne résout rien seul — voir Q2 |
| **2** | **Option 1 + combler l'asymétrie fr/en** dans `config/roles.yaml` | la page française devient PRESTATAIRE | **modifie un fichier métier gelé** · impact à mesurer sur les 731 tests et sur le score 55 |
| **3** | **Ne rien changer** et traiter le bruit par la réévaluation après collecte (Q2) | aucun risque immédiat | 11 pages inutiles entrent dans la rotation de visites |

**Ma recommandation : option 1 maintenant, option 2 séparément et mesurée.**
L'option 1 ne touche aucun fichier gelé et supprime la promotion sur
l'incertitude. L'option 2 est une vraie question métier qui mérite son propre
chantier, avec mesure d'impact avant/après sur la page de référence.

**Et le taux ne doit pas être l'objectif.** 2/55 n'est pas meilleur que 11/55
parce que le nombre est plus petit. Le seul juge est la qualité des
opportunités produites — qui n'est pas mesurable tant que l'egress bloque.
Régler ce curseur sur cette seule page serait l'erreur déjà payée deux fois.

---

## Q2 — RÉÉVALUER UNE CANDIDATE APRÈS COLLECTE

### Le constat

Aujourd'hui une candidate est jugée sur **trois mots de libellé**. C'est le
matériau le plus pauvre du projet. Après collecte on dispose de la page
entière, de ses segments portés, de ses blocs et de sa porte d'entrée — et on
n'en fait rien pour la qualification.

C'est le déséquilibre central : **on décide avec peu, alors qu'on pourrait
décider avec beaucoup, un instant plus tard.**

### Modèle proposé

**Les états ne changent pas.** `CANDIDATE` · `SURVEILLÉE` · `ÉCARTÉE` suffisent.
Ajouter un état « qualifiée » créerait une quatrième notion qui se confondrait
avec l'opportunité. Ce qui change, c'est **ce qui justifie la transition**.

```
CANDIDATE  ──(libellé : indice fort)──────────────→  SURVEILLÉE
    │
    └──(collectée une fois, sur décision)──→  CONTENU RÉEL
                                                  │
            ┌─────────────────────────────────────┼──────────────────┐
            ↓                                     ↓                  ↓
    indice fort sur le contenu            rien de probant      contre-preuve
            ↓                                     ↓                  ↓
        SURVEILLÉE                           CANDIDATE           CANDIDATE
   raison = preuve du contenu          raison mise à jour     + motif écrit
```

**Aucune candidate n'est supprimée, jamais.** Une réévaluation négative met à
jour la raison ; elle ne supprime ni ne rétrograde. `ÉCARTÉE` reste une
décision humaine.

**Les transitions :**

| Depuis | Vers | Condition | Qui décide |
|---|---|---|---|
| CANDIDATE | SURVEILLÉE | indice fort sur le **contenu réel** | `pertinence.evaluer` sur la page entière |
| CANDIDATE | CANDIDATE | rien de probant | raison mise à jour, page conservée |
| SURVEILLÉE | — | jamais rétrogradée automatiquement | seul l'exploitant écarte |
| ÉCARTÉE | — | jamais réveillée automatiquement | déjà garanti et testé |

**Les preuves.** La raison devient explicite sur son origine :
`PROMUE APRÈS COLLECTE — CONTENU — ROLE=PRESTATAIRE — « partenaire de livraison »`
contre l'actuelle `PROMUE AUTOMATIQUEMENT — …` qui ne dit pas sur quoi.

**La provenance** ne change pas : `provenances_pages` enregistre déjà chaque
rencontre. Une réévaluation n'est pas une rencontre — elle ne crée aucune
provenance.

**La persistance** : deux colonnes sur `pages_surveillees` —
`qualifiee_le` et `qualification` (le verdict de la dernière réévaluation).
Aucune table nouvelle. La déduplication est inchangée : on réévalue une page
existante, on n'en crée pas.

### Ce qui empêche « le mot transport transforme une page quelconque en opportunité »

**Trois garde-fous, tous déjà dans le projet :**

1. **Une page surveillée n'est pas une opportunité.** La promotion décide
   qu'on **revisitera** la page. L'opportunité, elle, naît de la chaîne, avec
   son rôle, son état, sa nature, son score. Les deux objets restent distincts,
   et c'est déjà testé.
2. **La portée.** Sur la page entière, `radar/portee.py` distingue déjà un
   terme lu dans le corps d'un terme lu dans un menu ou un pied de page. Une
   page de connexion dont seul le pied de page parle de colis ne produirait
   plus d'indice fort.
3. **La règle de rôle gelée.** « Fourniture et livraison de poissons » reste
   MOYENNE. C'est déjà prouvé.

### Coût et risque

Modéré. Deux colonnes, une fonction de réévaluation, un appel dans `Veille`.
**Aucun fichier gelé touché.** Le risque principal est de faire passer la
qualification pour une analyse commerciale : il se traite par le vocabulaire
d'affichage et par un test qui vérifie qu'une page surveillée n'est pas
comptée comme opportunité.

---

## Q3 — ATTRIBUTION → TITULAIRE → ENTREPRISE → SURVEILLANCE

### Le problème, énoncé exactement

Une attribution donne `titulaire = « Transports Exemple SRL »`. Elle ne donne
pas `exemple.be`. **Fabriquer l'URL à partir du nom est interdit** — et ce
n'est pas seulement une règle, c'est une garantie : un nom inventé pollue le
registre pour toujours, et une URL devinée ferait consulter un site qui n'a
rien à voir.

### Ce qui existe déjà et qui n'est pas utilisé

| Élément | État |
|---|---|
| table `attributions` | 17 colonnes, dont `titulaire`, `zone`, `prestation`, `contact` |
| colonne `entreprises.bce` | **existe, vide, jamais écrite** |
| `Registre.depuis_attribution()` | écrit le titulaire au registre, **sans domaine** |
| BCE/KBO dans la matrice des sources | cartographiée, `kbopub.economie.fgov.be`, libre, open data |

### L'architecture correcte

Le maillon manquant n'est pas un moteur de recherche. C'est **une source
d'identité d'entreprise faisant autorité**.

```
ATTRIBUTION
    ↓
TITULAIRE (une raison sociale, rien de plus)
    ↓
ENTREPRISE au registre           ← déjà fait, déjà persisté
    identite = INCONNUE
    ↓
RÉSOLUTION D'IDENTITÉ            ← le maillon manquant
    ↓
    ├── BCE/KBO : raison sociale → numéro d'entreprise → site déclaré
    ├── l'exploitant saisit le domaine à la main
    └── un moteur de découverte (quand il y en aura un)
    ↓
ENTREPRISE
    identite = CONFIRMÉE (source + date)  ou  AMBIGUË (n candidats)
    domaine  = celui que la SOURCE déclare, jamais celui qu'on suppose
    ↓
PAGES CANDIDATES                 ← seulement si un domaine est CONFIRMÉ
    ↓
SURVEILLANCE
```

**Un état d'identité, explicite et jamais deviné :**

| État | Sens |
|---|---|
| `INCONNUE` | on a un nom, rien d'autre. **État par défaut, et il est honnête.** |
| `AMBIGUË` | plusieurs entités portent ce nom — on conserve les candidats, on ne choisit pas |
| `CONFIRMÉE` | une source faisant autorité donne le domaine, avec sa date |
| `SANS SITE` | la source est formelle : cette entreprise n'a pas de site déclaré |

`SANS SITE` compte autant que `CONFIRMÉE` : c'est une mesure, pas un échec.
Et `INCONNUE ≠ 0` — la règle du projet s'applique telle quelle.

### Trois voies de résolution, et leur état réel

| Voie | Légalité | Accès depuis notre environnement | Verdict |
|---|---|---|---|
| **BCE/KBO open data** — l'entreprise déclare elle-même son site | libre, open data belge | `kbopub.economie.fgov.be` **HTTP=000 · egress bloqué** (mesuré ce jour) | 🟢 la bonne voie, **inaccessible aujourd'hui** |
| **Saisie par l'exploitant** | évidemment | aucun réseau requis | 🟢 **disponible immédiatement** |
| **Moteur de découverte** | selon le moteur | aucun moteur accessible | 🔴 bloqué |

Deux réserves que je dois poser :

- Je **n'ai pas vérifié** que l'open data BCE publie effectivement le site web
  des entreprises — l'hôte est bloqué et je refuse de l'affirmer sans l'avoir
  lu. À porter comme **`À VÉRIFIER`**, pas comme un acquis.
- Un homonyme est fréquent en Belgique. Sans numéro d'entreprise, une
  correspondance par nom seul doit sortir **AMBIGUË**, jamais un choix arbitraire.

### Ce qui est faisable maintenant, sans aucun réseau

1. **Poser l'état d'identité** sur `entreprises` (`identite`, `identite_source`,
   `identite_le`) et l'afficher. Le registre dirait enfin *« 12 titulaires
   connus, 12 identités INCONNUES »* — aujourd'hui il ne le dit pas.
2. **Une commande `radar identifier <entreprise> --domaine …`** : l'exploitant
   confirme, la source est `exploitant`, la date est écrite. C'est la seule
   voie ouverte, et elle est parfaitement légitime.
3. **Le branchement titulaire → pages candidates** ne s'active que sur une
   identité CONFIRMÉE. Sans domaine, il ne se passe rien — et c'est correct.

---

## CE QUE JE PROPOSE POUR L'ÉTAPE 7

Dans cet ordre, et **seulement après votre validation** :

| | Chantier | Fichiers gelés | Réseau requis |
|---|---|---|---|
| **7a** | Q1 option 1 — la promotion exige une preuve positive, plus jamais l'incertitude | aucun | non |
| **7b** | Q2 — réévaluation après collecte, deux colonnes, aucun nouvel état | aucun | non |
| **7c** | Q3 — état d'identité + `radar identifier`, branchement conditionné | aucun | non |
| **7d** | Q1 option 2 — asymétrie fr/en de `config/roles.yaml` | **`config/roles.yaml`** | non |

**7d est à part.** C'est le seul qui touche une règle métier gelée. Il devrait
être son propre chantier, avec mesure d'impact avant/après sur la page de
référence et sur les 731 tests.

## CE QUE JE NE FERAI PAS SANS VOUS L'AVOIR DEMANDÉ

- toucher `config/roles.yaml`, `config/capacites.yaml` ou `config/ponderations.yaml` ;
- régler un seuil pour obtenir un nombre de promotions qui « paraît bon » ;
- affirmer que l'open data BCE publie les sites web sans l'avoir lu ;
- créer un quatrième état de page, qui se confondrait avec l'opportunité.
