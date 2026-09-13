# 8e-4 — BRANCHER UNE SOURCE DE DÉCOUVERTE

Le radar ne dépend d'aucun fournisseur. Une source de découverte est un
**adaptateur interchangeable**, et il y en a trois formes.

---

## Les deux chemins

```
MOTEUR RÉEL (Brave, ou autre, ou une API future autorisée)
  ↓  radar/moteurs_recherche.py — un adaptateur qui implémente le contrat
  ↓  Resultat
  ↓  trouvailles.depuis_moteur(cx, moteur, resultats)   ← lit moteur.mode
  ↓  trouvailles
```

```
MOTEUR EXTERNE — exécuté ailleurs, hors du radar
  ↓  JSON ou CSV portant « provenance: EXÉCUTÉ HORS RADAR »
  ↓  radar/import_externe.py — charger() puis inscrire()
  ↓  trouvailles   (source « import:<moteur> », journal des exécutions)
```

Les deux débouchent au même endroit, et la suite est **identique** :

```
trouvailles → chainage.chainer()  → entreprise INCONNUE + page CANDIDATE
            → collecte réelle     → pages.marquer()
            → qualification (7b)  → pages.qualifier()
            → identité (7c)       → identite.confirmer()
            → surveillance        → pages.promouvoir()
            → opportunité         → la chaîne d'analyse
```

**Aucun maillon ne se saute, quelle que soit la porte d'entrée.**

---

## Ajouter un moteur réel

Trois choses à fournir, et rien d'autre :

```python
@dataclass
class UnMoteur(MoteurRecherche):
    nom: str = "un-moteur"

    @property
    def disponible(self) -> bool: ...
    @property
    def motif_indisponibilite(self) -> str | None: ...
    def rechercher(self, requete) -> list[Resultat]: ...
```

`mode` vaut `RÉEL` par héritage. La clé se lit **uniquement** dans
l'environnement (`depuis_environnement`), jamais dans le code, jamais dans un
fichier de configuration versionné.

Le moteur ne connaît **ni** le score, **ni** les catégories, **ni** le profil
commercial, **ni** le registre, **ni** aucune règle métier. Il rend des
résultats. C'est vérifié par test, sur les imports et les identifiants.

---

## Format d'un export externe

### JSON

```json
{
  "provenance": "EXÉCUTÉ HORS RADAR",
  "moteur": "nom-du-moteur",
  "date_execution": "2026-09-12T09:30:00+00:00",
  "resultats": [
    {"requete": "...", "url": "https://...", "titre": "...",
     "extrait": "...", "rang": 1}
  ]
}
```

`moteur` et `date_execution` peuvent aussi être portés **par ligne** : un même
fichier peut donc contenir plusieurs moteurs.

Un fichier avec `"resultats": []` et une `requete` en en-tête déclare
**« cette requête a été passée, rien n'est revenu »** — c'est `0`, une mesure,
et non `NON MESURÉ`.

### CSV

```
provenance,moteur,date_execution,requete,url,titre,extrait,rang
EXÉCUTÉ HORS RADAR,nom-du-moteur,2026-09-12T10:00:00+00:00,une requête,https://...,Titre,Extrait,3
```

Exemples complets : `fixtures/import-externe-exemple.json` et `.csv`.

### Usage

```python
from radar import import_externe as imp
bilan = imp.importer(cx, "export.json")
print(bilan.resume())      # dont la liste des lignes refusées
```

---

## Ce que le fichier doit déclarer, sous peine de refus

| Règle | Effet si non respectée |
|---|---|
| `provenance: EXÉCUTÉ HORS RADAR`, en en-tête **ou** sur **toutes** les lignes | `ImportInvalide` — le fichier entier est refusé |
| `moteur` présent | la ligne est refusée (`MOTEUR ABSENT`) |
| `url` en `http`/`https`, sans espace ni caractère de contrôle, ≤ 2048 | la ligne est refusée (`URL INVALIDE` / `URL TROP LONGUE`) |
| `titre` ≤ 500, `extrait` ≤ 2000, `requete` ≤ 500 | la ligne est refusée (`… HORS LIMITE`) |

Et ce qui **ne fait jamais refuser** une ligne :

| Anomalie | Traitement |
|---|---|
| `rang` illisible, négatif, nul, hors borne | rang **inconnu** — jamais renuméroté d'après la position |
| `date_execution` illisible | `INCONNUE` — **jamais** la date du jour |
| caractères de contrôle, marque de direction, espace de largeur nulle | retirés et **comptés** ; les mots sont conservés |
| même URL deux fois dans le fichier | comptée en doublon, la **première** occurrence garde son rang |

**Aucun refus n'est silencieux** : `bilan.resume()` les liste tous, ligne par
ligne, avec leur motif.

---

## Les quatre états, et pourquoi ils existent

| État | Ce qu'il dit |
|---|---|
| `RECHERCHE RÉELLE PAR LE RADAR` | nous avons interrogé un moteur nous-mêmes |
| `RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE` | un moteur a répondu, ailleurs ; on nous a remis le fichier |
| `FIXTURE / DEMO` | personne n'a rien interrogé ; les résultats sont fabriqués |
| `NON MESURÉ` | rien n'a été tenté — et ce **n'est pas** zéro |

`radar/execution.py` les porte ; `execution.rapport(cx)` est le seul rapport
qui les sépare tous les quatre.

**Un import ne peut pas gonfler les chiffres d'un moteur réellement
interrogé** : la source est qualifiée par le préfixe `import:`, donc
`un-moteur` et `import:un-moteur` sont deux sources distinctes dans toutes les
métriques. Le préfixe est **en tête** du nom parce que les rapports tronquent
les noms à droite — une marque en fin de nom disparaîtrait au premier
alignement de colonne.

---

## ÉTAT DES FOURNISSEURS

Ce tableau est un **constat de mesure**, pas une règle d'architecture. Aucune
ligne de code ne dépend de son contenu, et le radar fonctionne avec n'importe
quelle source autorisée le jour où elle existe.

| Fournisseur | État | Preuve |
|---|---|---|
| Google Custom Search JSON API | 🔴 **FERMÉ POUR NOTRE PROJET** | `403 PERMISSION_DENIED` réel, sur le projet de l'exploitant |
| Google Grounding (Vertex / Gemini) | 🔴 **INCOMPATIBLE AVEC NOTRE USAGE** | `cloud.google.com/terms/service-terms`, clause 20(k)(i)(2), lue à la source : collecte programmatique de liens, constitution d'un index, et usage des liens pour identifier des pages à collecter — les trois interdits sont exactement ce que fait le radar |
| Bing Search API | 🔴 **RETIRÉE** | service arrêté par l'éditeur |
| Brave Search API | 🟠 **À VÉRIFIER** | 8e-3 : aucune clause n'a pu être lue. `brave.com` et `api-dashboard.search.brave.com` sont hors du mur d'egress (HTTP 000). **DOCUMENTATION NON ACCESSIBLE — NON MESURÉ** |
| SerpAPI, Serper, et autres revendeurs | ⚪ **NON MESURÉS** | jamais testés, conditions jamais lues, aucun accès depuis cet environnement |
| Export produit hors radar | 🟢 **DISPONIBLE** | `radar/import_externe.py`, éprouvé par 63 tests — mais **le fichier reste à produire ailleurs**, et les conditions du moteur qui le produit restent celles du moteur |

⚠️ Le dernier point mérite d'être dit en clair : **déplacer la machine ne
déplace pas la restriction contractuelle.** L'import résout le problème
d'**accès réseau**, pas la question de savoir ce qu'un fournisseur autorise à
stocker. Ce sont deux questions séparées, et 8e-4 n'en règle qu'une.
