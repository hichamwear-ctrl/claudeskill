# LES DEUX CIRCUITS DU RADAR — audit de l'architecture existante

Date : 2026-09-13 · **Aucun code modifié** · 635 tests verts

## LA RÈGLE

> **Google et les autres moteurs servent principalement à découvrir ce que nous ne
> connaissons pas. Les sources que le radar connaît déjà doivent pouvoir être
> analysées directement, surveillées et transformées en opportunités sans dépendre
> d'un moteur de recherche.**

Trois interdits qui en découlent, à vérifier dans le code :

| Interdit | Présent aujourd'hui ? |
|---|---|
| `pas de Google → pas d'opportunité` | **NON** — le circuit fichier est complet et prouvé |
| `pas de moteur → pas de surveillance` | **OUI** — `Boucle.parcourir` ne revisite une entreprise que par requête |
| `source connue → obligation de passer par un moteur` | **OUI** — `cmd_surveiller` annonce l'attente d'une clé Google |

---

## RÉPONSES AUX HUIT QUESTIONS

### 1. La collecte directe des sources connues fonctionne-t-elle déjà ?

**OUI depuis un FICHIER. NON depuis une URL.**

`radar traiter --source <nom> --entree <fichier>` traverse toute la chaîne sans
toucher à un moteur. Huit adaptateurs déclaratifs existent :
`ted` · `bda` · `entreprise` · `page_web` · `portail` · `recherche` · `signaux` · `bourse_fret`.

Mais **`radar/` ne contient aucun récupérateur de page.** Les seuls appels réseau
du moteur sont `moteurs_recherche.py` (les moteurs) et `robots.py` (dont l'ouvreur
est injectable et que rien dans `radar/` n'appelle). La récupération réelle vit
dans `outils/` — `collecter_ted.py`, `collecter_bda.py` — et `premiere_page_reelle.py`
reçoit des **octets déjà obtenus**, il ne va pas les chercher.

> **Le circuit A existe à partir de l'octet. Il manque le pas qui va chercher l'octet.**

### 2. Le registre permet-il de conserver une entreprise durablement ?

**PARTIELLEMENT — et c'est le défaut le plus grave.**

La table `entreprises` existe (15 colonnes, index sur l'état). Mais :

```
radar/cli.py:222    INSERT OR REPLACE INTO entreprises   ← cmd_surveiller, AJOUT MANUEL
radar/cli.py:201    SELECT * FROM entreprises            ← cmd_entreprises, LECTURE
```

**Ce sont les deux seuls accès à la table dans tout le projet.**

Or la chaîne alimente bien un registre :

```
radar/chaine.py:692    moteur.entreprises.depuis_attribution(opp)    # le titulaire
radar/chaine.py:694    moteur.entreprises.depuis_opportunite(opp)    # l'acheteur
```

…mais `_moteur(cx)` (cli.py) ne passe **aucun** argument `entreprises=`, donc
`chaine.py:108` lui fabrique un registre **vide, en mémoire**, à chaque exécution :

```python
self.entreprises = entreprises if entreprises is not None else RegistreEntreprises()
```

**Conséquence mesurable : chaque `radar traiter` découvre des entreprises et les
perd à la sortie du processus.** Idem pour `cmd_boucle`, qui crée son propre
`RegistreEnt()` et ne l'écrit jamais.

> Seule une entreprise ajoutée **à la main** survit. Toutes celles que le radar
> découvre **tout seul** disparaissent. C'est exactement ce que la règle interdit.

### 3. Une entreprise peut-elle être surveillée sans moteur de recherche ?

**NON.** `Boucle.parcourir` n'a qu'un seul chemin de revisite :

```python
for e in self.entreprises.a_surveiller(limite=5):
    for q in self.generateur.pour_entreprise(e.nom, e.domaine):
        file.append((profondeur + 1, q, e.nom))
```

`pour_entreprise()` produit des requêtes `site:` — inexploitables sans moteur.
**Il n'existe aucune branche « entreprise connue → récupérer ses pages directement ».**

### 4. Une nouvelle page peut-elle devenir une opportunité sans passer par Google ?

**OUI — prouvé aujourd'hui**, en rejouant la page Colis Privé archivée avec
`GOOGLE_API_KEY`, `GOOGLE_CSE_ID` et `BRAVE_API_KEY` **retirées de l'environnement** :

```
url      https://www.colisprive.be/devenir-partenaire-livraison/
sha256   c5e20010e7bd92c7a5d28462c32169ce34bc8df194014f85838be09b15df08a0
→ 6 pistes sur 7 répondent · 3 champs OBSERVÉS · 6 champs INCONNUS avec leur question
→ 🟢 DIRECT · moteur CAPTER · score 55/100 · PORTE D'ENTRÉE FORMULAIRE · 👉 POSTULER
```

Zéro moteur. Chaîne complète : rôle → ontologie → état → nature → fiabilité →
capacités → score → classification → action → fiche commerciale.

### 5. DÉVELOPPER peut-il fonctionner sans moteur ?

**OUI pour la mémoire, NON pour la relance.**

La table `attributions` est écrite par `chaine.py`, et `radar calendrier` calcule
les remises en concurrence sans aucun moteur. ✅

Mais `depuis_attribution(opp)` range le titulaire dans le registre **en mémoire**
(question 2) : il n'est jamais réécrit en base, donc jamais surveillé ensuite.
**La chaîne « TED dit que X a gagné → surveiller X » est écrite, mais sa mémoire fuit.**

### 6. Les signaux peuvent-ils fonctionner sans moteur ?

**OUI structurellement** — `sources/signaux.yaml` est un adaptateur comme les
autres, consommé par `traiter`. Aucun moteur requis.

**Mais aucune source de signaux n'est atteignable aujourd'hui** (famille F mesurée
bloquée par l'egress). Le circuit est prêt ; le robinet est fermé. `NON MESURÉE ≠ 0`.

### 7. Où se trouve exactement la dépendance à `MoteurRecherche` ?

Elle est **remarquablement petite** — c'est la bonne nouvelle de cet audit.

| Emplacement | Nature |
|---|---|
| `radar/decouverte.py:118` | le seul `import` des moteurs dans tout le moteur |
| `radar/cli.py` · `_registre()` | déclare `google` comme source du registre |
| `radar/cli.py` · `cmd_boucle` | la commande de découverte |
| `radar/cli.py` · `cmd_requetes` | affiche les requêtes prêtes |
| `radar/cli.py` · `cmd_surveiller` | affiche les requêtes ciblées |

**`chaine.py`, `score.py`, `classification.py`, `procedure.py`, `fiche.py`,
`portee.py`, `capacite.py`, `nature.py`, `suivi.py`, `porte.py` : aucune référence
à un moteur.** Le cœur est déjà indépendant. `Boucle` reçoit `chercher` en argument
et ne sait pas d'où viennent les résultats.

### 8. Où le code suppose-t-il à tort qu'un moteur est obligatoire ?

**Quatre endroits, tous en périphérie, aucun dans le cœur.**

| # | Emplacement | Ce qu'il fait de faux |
|---|---|---|
| **D1** | `cli.py` · `cmd_surveiller` | *« seront lancées dès qu'une clé Google sera disponible »* — une entreprise **connue** est annoncée comme en attente d'un moteur. C'est littéralement `source connue → obligation de passer par un moteur`. |
| **D2** | `boucle.py` · `Boucle.parcourir` | la revisite d'une entreprise connue passe **uniquement** par `chercher(requete)`. C'est `pas de moteur → pas de surveillance`. |
| **D3** | `cli.py` · `cmd_requetes` | *« le connecteur **Google** est indisponible »* — nomme Google alors que le registre en contient deux. Google redevient le modèle implicite. |
| **D4** | `cli.py` · `_registre()` | déclare `google` au registre des sources, **pas `brave`**. Brave existe dans le code mais reste invisible dans l'état des sources. |

**Ce qui est déjà juste**, et qu'il ne faut pas toucher :
`moteurs_recherche.Registre.rapport()` dit déjà —
*« Aucun moteur disponible : la découverte web ne peut pas démarrer. **Le radar
fonctionne quand même sur ses autres sources.** »*

---

## CORRECTIONS PROPOSÉES — NON CODÉES

| # | Correction | Pourquoi | Ampleur |
|---|---|---|---|
| **C1** | `_moteur(cx)` charge le registre d'entreprises depuis la base, et `traiter()` le réécrit en fin de lot | **une entreprise découverte ne doit jamais disparaître** | moyenne — une lecture, une écriture, aucun changement de logique |
| **C2** | Nouvelle table `pages_surveillees(cle_entreprise, url, chemin, derniere_visite, empreinte, etat)` | une entreprise a **plusieurs** pages ; aujourd'hui elle n'a qu'un `domaine` | moyenne — table neuve, rien de modifié |
| **C3** | Nouveau module `radar/collecte_directe.py` : `recuperer(url) -> octets`, **robots.txt obligatoire** via `radar/robots.py`, délai respecté | c'est le pas manquant du circuit A ; `robots.py` existe déjà et n'attend que cela | moyenne — module neuf, `robots.py` inchangé |
| **C4** | `Boucle` reçoit une seconde branche `surveiller(entreprise) -> [pages]` indépendante de `chercher` | supprime D2 sans toucher à la branche découverte | moyenne |
| **C5** | Réutiliser la table `filigrane` (**déclarée, jamais utilisée**) pour l'empreinte de chaque page surveillée → détection de changement | le créneau existe déjà dans le schéma | petite |
| **C6** | `cmd_surveiller` : afficher d'abord ce qui est possible **maintenant** sans moteur, et présenter les requêtes ciblées comme un **complément** | supprime D1 | petite — texte seul |
| **C7** | `cmd_requetes` : *« aucun moteur de recherche n'est disponible »*, avec le motif de **chacun** | supprime D3 | petite — texte seul |
| **C8** | `_registre()` : déclarer **tous** les moteurs du registre, pas `google` en dur | supprime D4 | petite |
| **C9** | Champ `circuit` (`SOURCE_CONNUE` / `SOURCE_DÉCOUVERTE`) sur les provenances, et métriques séparées DÉCOUVERTE / SURVEILLANCE | §11 et §12 de la règle : savoir si une opportunité vient de découvrir ou de surveiller | moyenne |

**Aucune de ces corrections ne touche au score, à la classification, à la nature,
à l'état, à la procédure, à la portée, aux capacités, à la fiche ni au suivi.**
Les composants gelés restent gelés.

### Ce qui reste absolument interdit

`SOURCE ≠ QUALITÉ` : le circuit (connu ou découvert) et le moteur d'origine
entrent dans la **provenance** et dans les **métriques**, **jamais** dans le score.
Une opportunité vue par surveillance directe et une opportunité vue par Google
décrivant le même besoin reçoivent le **même score**.
